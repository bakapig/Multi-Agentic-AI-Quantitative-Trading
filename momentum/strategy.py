import numpy as np
import pandas as pd
from .config import *
from .garch import fit, filter_h


def cost_vec(cols):
    return np.array([COST_BPS.get(c, COST_BPS[".SI"] if c.endswith(".SI") else COST_BPS["default"]) / 1e4 for c in cols])


def garch_forecast_one(v, resume=None):
    """Walk-forward forecasts for one return series v (percent). Refits start at GARCH_MIN_OBS and recur every REFIT_EVERY obs.
    resume=(s, par) restarts at the refit block s with its stored parameters (no refit there), so the result equals a full run.
    Returns (forecast array in decimal, (s_last, par_last))."""
    fc, par, first = np.full(len(v), np.nan), None, GARCH_MIN_OBS
    if resume is not None:
        first, par = resume[0], np.asarray(resume[1], float)
    last = None
    for s in range(first, len(v), REFIT_EVERY):
        lo, end = max(0, s - GARCH_WINDOW), min(len(v), s + REFIT_EVERY)
        if resume is None or s != first:
            par = fit(v[lo:s + 1], par)
        h = filter_h(v[lo:end], *par[:3])
        fc[s:end] = np.sqrt(h[s + 1 - lo:end + 1 - lo]) / 100
        last = (s, par)
    return fc, last


def garch_vol_forecasts(raw, cache=None, state=None):
    """Walk-forward daily vol forecast (decimal), known at close t for t+1, per asset on its own trading calendar.
    Parameters are refit every REFIT_EVERY days on a rolling window ending at t; between refits only the filter is updated.
    state (dict, optional) is filled with {asset: (s_last, par_last)} so the forecasts can later be extended incrementally."""
    if cache is not None and cache.exists():
        return pd.read_csv(cache, index_col=0, parse_dates=True)
    out = {}
    for c in raw.columns:
        v = 100 * np.log(raw[c].dropna()).diff().dropna()
        fc, last = garch_forecast_one(v.values)
        out[c] = pd.Series(fc, index=v.index)
        if state is not None:
            state[c] = last
        print("garch", c, np.round(last[1], 4), flush=True)
    df = pd.DataFrame(out)
    if cache is not None:
        df.to_csv(cache)
    return df


def extend_garch_forecasts(raw, old, state):
    """Incremental update: keep forecasts before each asset's last refit block, recompute from that block with stored parameters,
    and refit only at new blocks. state is updated in place. Equals garch_vol_forecasts on the full data (up to the block's
    initial-variance start value, which fades geometrically). Returns (forecasts, first date that was recomputed)."""
    out, first = {}, []
    for c in raw.columns:
        v = 100 * np.log(raw[c].dropna()).diff().dropna()
        s0 = state[c][0]
        fc, last = garch_forecast_one(v.values, resume=state[c])
        vals = old[c].reindex(v.index).values.copy()
        vals[s0:] = fc[s0:]
        out[c], state[c] = pd.Series(vals, index=v.index), last
        first.append(v.index[s0])
    return pd.DataFrame(out), min(first)


def trend_signal(ff, lookbacks=LOOKBACKS):
    """Mean of sign(past L-day log return), in [-1, 1]; uses prices up to t only."""
    return sum(np.sign(np.log(ff / ff.shift(L))) for L in lookbacks) / len(lookbacks)


def build_weights(ff, vol_d, sig, long_only=False, target=TARGET_VOL, max_lev=MAX_LEVERAGE):
    """Weights decided at close t: raw w_i = s_i / sigma_i (GARCH), scaled so ex-ante portfolio vol = target
    (GARCH vols x rolling CORR_WINDOW correlation); gross leverage capped at max_lev."""
    r = np.log(ff).diff()
    vol = vol_d.reindex(ff.index).ffill() * np.sqrt(TRADING_DAYS)
    s = sig.clip(lower=0) if long_only else sig
    ok = (vol.notna() & s.notna()).values
    rv, vv, sv = r.values, vol.values, s.values
    W = np.zeros(ff.shape)
    for i in range(CORR_WINDOW, len(ff)):
        m = ok[i]
        if not m.any():
            continue
        idx = np.where(m)[0]
        raw = sv[i][idx] / vv[i][idx]
        if not raw.any():
            continue
        win = np.nan_to_num(rv[i - CORR_WINDOW + 1:i + 1][:, idx])
        C = np.corrcoef(win.T) if len(idx) > 1 else np.ones((1, 1))
        C = np.nan_to_num(C) + 1e-6 * np.eye(len(idx))
        D = raw * vv[i][idx]
        pv = np.sqrt(max(D @ C @ D, 1e-12))
        k = min(target / pv, max_lev / max(np.abs(raw).sum(), 1e-12))
        W[i, idx] = raw * k
    return pd.DataFrame(W, index=ff.index, columns=ff.columns)


def throttle(W, every, band, eta=1.0):
    """Trade only every `every`-th day, only assets whose target moved by > band*max(|target|,|held|) (always on sign change),
    and only a fraction eta of the way. Uses only weights known at t."""
    Wv, out, cur = W.values, np.zeros(W.shape), np.zeros(W.shape[1])
    for i in range(len(Wv)):
        if i % every == 0:
            tgt = Wv[i]
            mv = (np.abs(tgt - cur) > band * np.maximum(np.abs(tgt), np.abs(cur))) | (np.sign(tgt) != np.sign(cur))
            cur = np.where(mv, cur + eta * (tgt - cur), cur)
        out[i] = cur
    return pd.DataFrame(out, index=W.index, columns=W.columns)


def backtest(ff, W, lag=LAG):
    r = ff.pct_change().fillna(0.0)
    Wl = W.shift(lag).fillna(0.0)
    turn = Wl.diff().abs().fillna(0.0)
    net = (Wl * r).sum(1) - (turn * cost_vec(ff.columns)).sum(1)
    return net, turn, Wl


def run_blend(ff, gv, rf, lag=LAG):
    """Frozen strategy. Returns net daily returns (after trading costs AND financing) plus components."""
    ones = pd.DataFrame(1.0, index=ff.index, columns=ff.columns)
    Wt = throttle(build_weights(ff, gv, trend_signal(ff)), TREND_EVERY, TREND_BAND, TREND_ETA)
    Wc = throttle(build_weights(ff, gv, ones, long_only=True), CORE_EVERY, CORE_BAND)
    nt, tt, Lt = backtest(ff, Wt, lag)
    nc, tc, Lc = backtest(ff, Wc, lag)
    gross = W_TREND * Lt.abs().sum(1) + W_CORE * Lc.abs().sum(1)
    fin_of = lambda g: (g - 1).clip(lower=0) * (rf + FIN_SPREAD / TRADING_DAYS)
    fin = fin_of(gross)
    return dict(net=W_TREND * nt + W_CORE * nc - fin, trend=nt - fin_of(Lt.abs().sum(1)), core=nc - fin_of(Lc.abs().sum(1)),
                W=W_TREND * Wt + W_CORE * Wc, Wlag=W_TREND * Lt + W_CORE * Lc, turn=W_TREND * tt + W_CORE * tc, gross=gross, fin=fin)


def trade_log(Wl, ff):
    """A trade = a run of constant position sign in one asset; P&L = sum of w*r over the run (before costs)."""
    r = ff.pct_change().fillna(0.0)
    rows = []
    for c in Wl.columns:
        sg = np.sign(Wl[c].round(8))
        run = (sg != sg.shift()).cumsum()
        contrib = Wl[c] * r[c]
        for _, idx in sg.groupby(run).groups.items():
            if sg.loc[idx[0]] != 0:
                rows.append(dict(asset=c, side=int(sg.loc[idx[0]]), start=idx[0], end=idx[-1], days=len(idx), pnl=contrib.loc[idx].sum()))
    return pd.DataFrame(rows)
