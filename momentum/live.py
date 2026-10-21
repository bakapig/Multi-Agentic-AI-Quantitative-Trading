"""Daily auto-update of the frozen momentum strategy (paper only, no orders). Run after the US close:
    python scripts/run_momentum_daily.py [--no-refresh] [--full-refit] [--as-of-utc YYYY-MM-DD]
Steps: refresh prices -> pin frozen history, keep completed bars only -> report history drift -> extend GARCH-t forecasts -> weights -> live/momentum outputs.
Signals are computed at close t and filled at the next close (lag 2). Parameters in config.py are frozen and never re-tuned here."""
import argparse, hashlib, json, warnings
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from .config import *
from .data import download, weekday_panel, rf_daily
from .strategy import garch_vol_forecasts, extend_garch_forecasts, run_blend, trade_log
from .metrics import summary

CACHE, STATE = DATA / "garch_vol_forecasts.csv", DATA / "garch_state.json"
DRIFT_TOL = 1e-5                       # Yahoo adjusted-price rounding noise is ~1e-6 in daily log returns; larger = genuine revision
ANCHORS = ("SPY", "D05.SI")   # Both US and SGX must have posted the final bar


def drop_incomplete(s, now=None):
    """Keep bars dated strictly before today's UTC date; today's US/SGX bar may be incomplete."""
    now = now or datetime.now(timezone.utc)
    return s[s.index < pd.Timestamp(now.date())]


def trim_tail(px):
    """End the panel at the last date on which every anchor market has a bar. Yahoo posts bars late or inconsistently around the
    UTC date rollover, and an unposted bar would otherwise be forward-filled as a zero return."""
    ok = px[list(ANCHORS)].notna().all(axis=1)
    if not ok.any():
        raise RuntimeError("no date with a complete anchor cross-section")
    return px.loc[:ok[ok].index.max()]


def splice(old, new, end=SEEN_END):
    """Pin history up to `end` to the cached snapshot (so frozen-period inputs, GARCH state and reported results never move), and take
    later rows from `new`, rescaled onto the snapshot's adjustment basis: a later dividend rescales every earlier adjusted price in `new`,
    so levels cannot be mixed across the boundary. Bars `new` lacks keep their cached value."""
    pin, e = old.loc[:end], pd.Timestamp(end)
    k = new.loc[:end].ffill().iloc[-1] / pin.ffill().iloc[-1]
    k = k.where((k - 1).abs() > DRIFT_TOL, 1.0)          # below the rounding-noise floor: keep Yahoo's values untouched
    post = (new.loc[new.index > e] / k).combine_first(old.loc[old.index > e])
    return pd.concat([pin, post])[ASSETS]


def fetch():
    import yfinance as yf
    px = yf.download(ASSETS, start=DATA_START, auto_adjust=True, progress=False)["Close"][ASSETS].dropna(how="all")
    irx = yf.download("^IRX", start=DATA_START, progress=False, auto_adjust=False)["Close"].squeeze()
    for s in (px, irx):
        s.index = pd.DatetimeIndex(s.index).tz_localize(None)
    return px, irx


def history_drift(old, new, end=SEEN_END):
    """Assets whose daily log returns up to `end` differ between the cached and refreshed prices, plus rows that appeared or vanished.
    Adjusted-price rescaling by later dividends leaves returns unchanged, so any hit is a genuine revision."""
    a, b = np.log(old.loc[:end]).diff(), np.log(new.loc[:end]).diff()
    idx = a.index.intersection(b.index)
    d = (a.loc[idx] - b.loc[idx]).abs().max()
    return dict(returns={k: float(v) for k, v in d[d > DRIFT_TOL].items()}, rows_changed=int(len(a.index.symmetric_difference(b.index))))


def write_csv_keep_head(path, df, first_new, **kw):
    """Rewrite `path` keeping its existing lines dated before `first_new` byte for byte and writing df's rows from `first_new` on.
    A pandas CSV round trip can move floats by 1 ulp and the GARCH fits are sensitive to that, so frozen history is never re-serialised
    (this also keeps the daily git diff to the last few lines)."""
    first_new = pd.Timestamp(first_new)
    lines = path.read_text().splitlines()
    head = [ln for ln in lines[1:] if ln.split(",", 1)[0] < str(first_new.date())]
    body = df.loc[df.index >= first_new].to_csv(header=False, **kw).splitlines()
    path.write_text("\n".join([lines[0], *head, *body]) + "\n", newline="\n")


def save_state(state):
    STATE.write_text(json.dumps({c: dict(s=int(s), par=[float(x) for x in p]) for c, (s, p) in state.items()}))


def load_state():
    return {c: (v["s"], np.array(v["par"])) for c, v in json.loads(STATE.read_text()).items()}


def update_garch(raw, full):
    if full or not (CACHE.exists() and STATE.exists()):
        CACHE.unlink(missing_ok=True)
        state = {}
        gv = garch_vol_forecasts(raw, CACHE, state)
        mode = "full_refit"
    else:
        state = load_state()
        gv, first = extend_garch_forecasts(raw, pd.read_csv(CACHE, index_col=0, parse_dates=True), state)
        write_csv_keep_head(CACHE, gv, first)
        mode = "incremental"
    save_state(state)
    return gv, mode


def _clean(d):
    return {k: (None if pd.isna(v) else (int(v) if float(v).is_integer() and k in ("days", "n_trades", "dd_episodes") else float(v))) for k, v in d.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-refresh", action="store_true", help="use the cached prices; GARCH is still extended if the cache is behind")
    ap.add_argument("--full-refit", action="store_true", help="refit every GARCH block from scratch (about 20 seconds)")
    ap.add_argument("--as-of-utc", help="override 'now' (UTC date) for the completed-bar rule")
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    DATA.mkdir(parents=True, exist_ok=True); LIVE.mkdir(parents=True, exist_ok=True)
    now = datetime.fromisoformat(args.as_of_utc).replace(tzinfo=timezone.utc) if args.as_of_utc else datetime.now(timezone.utc)

    drift, full = dict(returns={}, rows_changed=0), args.full_refit
    if not args.no_refresh:
        old_px, old_irx = download()
        px, irx = fetch()
        drift = history_drift(old_px, px)
        e = pd.Timestamp(SEEN_END)
        px = splice(old_px, px)
        irx = pd.concat([old_irx.loc[:e], irx[irx.index > e].combine_first(old_irx[old_irx.index > e])])
        px, irx = trim_tail(drop_incomplete(px, now)), drop_incomplete(irx, now)
        if px.empty or px.index.max() < old_px.index.max() - pd.Timedelta(days=5):
            raise RuntimeError(f"refreshed prices end {px.index.max() if len(px) else None}, cached end {old_px.index.max()}; keeping the cache")
        if drift["returns"] or drift["rows_changed"]:
            print("NOTE: Yahoo revised pre-test history; the cached snapshot is kept (frozen inputs).", drift)
        write_csv_keep_head(DATA / "prices.csv", px, pd.Timestamp(SEEN_END) + pd.Timedelta(days=1), index_label="Date")
        write_csv_keep_head(DATA / "rf_irx.csv", irx, pd.Timestamp(SEEN_END) + pd.Timedelta(days=1), index_label="Date")
    px, irx = download()
    px = trim_tail(drop_incomplete(px, now))
    raw, ff = weekday_panel(px)
    rf = rf_daily(irx, ff.index)
    gv, mode = update_garch(raw, full)
    R = run_blend(ff, gv, rf)

    asof, tw, prev = R["W"].index[-1], R["W"].iloc[-1], R["W"].iloc[-2]
    log = LIVE / "daily_weights.csv"
    row = pd.concat([pd.Series({"asof": str(asof.date())}), tw.round(4)]).to_frame().T
    if log.exists():
        row = pd.concat([pd.read_csv(log).pipe(lambda o: o[o["asof"] != str(asof.date())]), row])
    row.to_csv(log, index=False)
    print(f"As of close {asof.date()} (completed bars only). Orders fill at the NEXT close.  GARCH update: {mode}")
    print("Target weights (% NAV, negative = short):\n", (100 * tw).round(1).to_string())
    d = (tw - prev)[(tw - prev).abs() > 1e-6]
    print("Change vs previous day:", "none" if d.empty else "\n" + (100 * d).round(2).to_string())
    print(f"Gross {tw.abs().sum():.2f}x, net {tw.sum():.2f}x")

    pd.DataFrame({"ticker": ASSETS, "sleeve_group": ["core"] * len(CORE_ASSETS) + ["breadth"] * len(BREADTH_ASSETS),
                  "market": ["SGX" if c.endswith(".SI") else "US-listed" for c in ASSETS]}).to_csv(LIVE / "assets.csv", index=False)
    px.loc[TEST_START:].to_csv(LIVE / "portfolio_closing_prices.csv", index_label="Date")
    t = R["net"].loc[TEST_START:]
    kpi = dict(status="awaiting_test_window", observations=0)
    if len(t):
        t.to_csv(LIVE / "test_period_returns.csv", header=["net_return"], index_label="Date")
        s = summary(t, rf, trade_log(R["Wlag"].loc[pd.Timestamp(EVAL_START):], ff), R["turn"])
        kpi = dict(status="ok", observations=len(t), window=[str(t.index[0].date()), str(t.index[-1].date())],
                   cumulative_return=float((1 + t).prod() - 1), **_clean(s.to_dict()),
                   note="Few observations: ratios are not statistically meaningful. Trade stats count trades opened inside the window.")
        print(f"\nLIVE TEST WINDOW from {TEST_START}: {len(t)} days, cumulative {kpi['cumulative_return']:.2%}, max_dd {s['max_dd']:.2%}")
    (LIVE / "portfolio_kpis.json").write_text(json.dumps(kpi, indent=2))
    (LIVE / "run_manifest.json").write_text(json.dumps(dict(
        last_close=str(asof.date()), run_utc=now.isoformat(timespec="seconds"), garch_update=mode, refreshed=not args.no_refresh,
        history_drift=drift, orders_enabled=False, execution="paper: signal at close t, fill at close t+1 (lag 2)", n_assets=len(ASSETS),
        config_sha256=hashlib.sha256((ROOT / "momentum" / "config.py").read_bytes()).hexdigest()), indent=2))
    return R


if __name__ == "__main__":
    main()
