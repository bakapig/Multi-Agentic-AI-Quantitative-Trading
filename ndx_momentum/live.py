"""Daily update of the NDX momentum-hedge strategy (paper only, no orders). Run after the US close:
    python scripts/run_ndx_momentum_daily.py [--no-refresh] [--as-of-utc YYYY-MM-DD]
Steps: refresh prices -> pin history to the cached snapshot, keep completed bars only -> report history drift -> current book and test-window returns
for each variant in config.VARIANTS -> live/ndx_momentum outputs. Parameters in config.py are frozen and never re-tuned here."""
import argparse
import hashlib
import json
import warnings
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from .config import *
from .data import PRICES, fetch, load_panel, needed_tickers, to_dict
from .strategy import current_book, daily_returns, window_stats

ANCHORS = (BENCH, HEDGE)


def drop_incomplete(df, now=None):
    """Keep bars dated strictly before today's UTC date; a bar for the current day may still be forming."""
    now = now or datetime.now(timezone.utc)
    return df[df.index < pd.Timestamp(now.date())]


def trim_tail(df):
    """End the panel at the last date on which QQQ and PSQ both have a bar (an unposted bar must not be read as a zero return)."""
    ok = df[list(ANCHORS)].notna().all(axis=1)
    if not ok.any():
        raise RuntimeError("no date with a complete QQQ/PSQ cross-section")
    return df.loc[:ok[ok].index.max()]


def splice(old, new, end=SEEN_END):
    """Pin history up to `end` to the cached snapshot and take later rows from `new`, rescaled onto the snapshot's adjustment basis
    (a later dividend rescales every earlier adjusted price in `new`). Bars `new` lacks keep their cached value."""
    cols = old.columns.union(new.columns)
    pin = old.loc[:end].reindex(columns=cols)
    k = new.reindex(columns=cols).loc[:end].ffill().iloc[-1] / pin.ffill().iloc[-1]
    k = k.where((k - 1).abs() > DRIFT_TOL, 1.0).fillna(1.0)
    e = pd.Timestamp(end)
    post = (new.reindex(columns=cols).loc[new.index > e] / k).combine_first(old.reindex(columns=cols).loc[old.index > e])
    return pd.concat([pin, post]).sort_index()


def history_drift(old, new, end=SEEN_END):
    """Tickers whose daily log returns up to `end` differ between the snapshot and the refresh (dividend rescaling leaves returns unchanged)."""
    cols = old.columns.intersection(new.columns)
    a, b = np.log(old.loc[:end, cols]).diff(), np.log(new.loc[:end, cols]).diff()
    idx = a.index.intersection(b.index)
    d = (a.loc[idx] - b.loc[idx]).abs().max()
    return dict(returns={k: float(v) for k, v in d[d > DRIFT_TOL].items()}, rows_changed=int(len(a.index.symmetric_difference(b.index))))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-refresh", action="store_true", help="use the cached snapshot only")
    ap.add_argument("--as-of-utc", help="override 'now' (UTC date) for the completed-bar rule")
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    LIVE.mkdir(parents=True, exist_ok=True)
    now = datetime.fromisoformat(args.as_of_utc).replace(tzinfo=timezone.utc) if args.as_of_utc else datetime.now(timezone.utc)

    drift = dict(returns={}, rows_changed=0)
    old = load_panel()
    if not args.no_refresh:
        new = fetch()
        drift = history_drift(old, new)
        panel = trim_tail(drop_incomplete(splice(old, new), now))
        if panel.empty or panel.index.max() < old.index.max() - pd.Timedelta(days=5):
            raise RuntimeError(f"refreshed prices end {panel.index.max() if len(panel) else None}, cached end {old.index.max()}; keeping the cache")
        if drift["returns"] or drift["rows_changed"]:
            print("NOTE: Yahoo revised pre-test history; the cached snapshot is kept for those rows (frozen inputs).", drift)
        panel.to_csv(PRICES, float_format="%.6f", index_label="Date")
    panel = trim_tail(drop_incomplete(load_panel(), now))
    prices = to_dict(panel)
    last = panel.index.max()
    missing = sorted(set(needed_tickers()) - set(prices))

    books, daily, picks_rows = {}, {}, []
    for name, v in VARIANTS.items():
        books[name] = b = current_book(prices, v["universe"], v["lag"])
        daily[name] = daily_returns(prices, TEST_START, str(last.date()), **v)
        picks_rows += [dict(asof=str(last.date()), variant=name, decided_at=b["decided_at"], fills_at=b["fills_at"], ticker=p["ticker"],
                            weight=round(p["weight"], 4), mom5=round(p["mom5"], 4), mom20=round(p["mom20"], 4), price=round(p["price"], 4)) for p in b["picks"]]
        picks_rows.append(dict(asof=str(last.date()), variant=name, decided_at=b["decided_at"], fills_at=b["fills_at"], ticker=HEDGE,
                               weight=HEDGE_FRAC, mom5=None, mom20=None, price=round(prices[HEDGE][str(last.date())], 4)))
    log = LIVE / "daily_picks.csv"
    new_rows = pd.DataFrame(picks_rows)
    if log.exists():
        o = pd.read_csv(log)
        new_rows = pd.concat([o[o["asof"] != str(last.date())], new_rows])
    new_rows.to_csv(log, index=False)

    for name, b in books.items():
        print(f"\n[{name}] decided at {b['decided_at']} close, fills {b['fills_at']}; next rebalance in {b['days_to_next_rebalance']} trading days; pool {b['pool_size']} names")
        for p in b["picks"]:
            print(f"  {p['ticker']:6s} w={p['weight']:.2f}  5d {100 * p['mom5']:6.1f}%  20d {100 * p['mom20']:6.1f}%  {p['price']:.2f}")
        print(f"  {HEDGE:6s} w={HEDGE_FRAC:.2f}  (1x inverse QQQ hedge)")

    ret = pd.DataFrame({n: d["strategy"] for n, d in daily.items()})
    ret["QQQ"] = next(iter(daily.values()))["qqq"] if daily else np.nan
    kpi = dict(status="awaiting_test_window", observations=0)
    if len(ret):
        ret.to_csv(LIVE / "test_period_returns.csv", index_label="Date")
        held = sorted({t for d in daily.values() for s in d["picks"] for t in s.split(",") if t} | {BENCH, HEDGE})
        panel.loc[TEST_START:, [t for t in held if t in panel.columns]].to_csv(LIVE / "portfolio_closing_prices.csv", index_label="Date")
        kpi = dict(status="ok", observations=len(ret), window=[str(ret.index[0].date()), str(ret.index[-1].date())], primary=PRIMARY,
                   variants={n: window_stats(ret[n]) for n in daily}, qqq=window_stats(ret["QQQ"]),
                   note="Few observations: ratios are not statistically meaningful. Daily returns treat weights as rebalanced daily inside each week.")
        print("\nTEST WINDOW", TEST_START, "->", last.date())
        for n in daily:
            s = kpi["variants"][n]
            print(f"  {n:30s} cumulative {s['cumulative_return']:+.2%}  max_dd {s['max_dd']:.2%}")
        print(f"  {'QQQ buy and hold':30s} cumulative {kpi['qqq']['cumulative_return']:+.2%}  max_dd {kpi['qqq']['max_dd']:.2%}")
    (LIVE / "portfolio_kpis.json").write_text(json.dumps(kpi, indent=2))
    (LIVE / "run_manifest.json").write_text(json.dumps(dict(
        last_close=str(last.date()), run_utc=now.isoformat(timespec="seconds"), refreshed=not args.no_refresh, history_drift=drift,
        unavailable_tickers=missing, orders_enabled=False, membership_anchor=ANCHOR_DATE,
        execution="paper; primary variant fills at the next close with 10 bp on stock turnover",
        config_sha256=hashlib.sha256((ROOT / "ndx_momentum" / "config.py").read_bytes()).hexdigest()), indent=2))
    return ret


if __name__ == "__main__":
    main()
