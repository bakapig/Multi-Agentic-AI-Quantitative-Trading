import numpy as np
import pandas as pd
from scipy import stats
from .config import TRADING_DAYS


def drawdown(ret):
    eq = (1 + ret).cumprod()
    return eq / eq.cummax().clip(lower=1.0) - 1


def dd_episodes(ret, min_depth=0.01):
    n, in_dd, depth = 0, False, 0.0
    for v in drawdown(ret).values:
        if v < 0:
            in_dd, depth = True, min(depth, v)
        elif in_dd:
            n, in_dd, depth = n + (depth <= -min_depth), False, 0.0
    return int(n + (in_dd and depth <= -min_depth))


def summary(ret, rf, trades=None, turn=None):
    """Brief metrics: annual return, vol, Sharpe (excess of T-bill), max drawdown, drawdown count (>1%), and trade statistics."""
    ret = ret.dropna()
    ex = ret - rf.loc[ret.index]
    out = dict(ann_return=(1 + ret).prod() ** (TRADING_DAYS / len(ret)) - 1, ann_vol=ret.std() * np.sqrt(TRADING_DAYS),
               sharpe_ex_rf=ex.mean() / ex.std() * np.sqrt(TRADING_DAYS), max_dd=drawdown(ret).min(), dd_episodes=dd_episodes(ret), days=len(ret))
    out["calmar"] = out["ann_return"] / -out["max_dd"]
    if trades is not None and len(trades):
        t = trades[(trades.start >= ret.index[0]) & (trades.end <= ret.index[-1])]
        out.update(n_trades=len(t), win_rate=(t.pnl > 0).mean(), avg_hold_days=t.days.mean(), profit_per_trade=t.pnl.mean())
    if turn is not None:
        out["ann_turnover"] = turn.loc[ret.index].sum(1).mean() * TRADING_DAYS
    return pd.Series(out)


def kupiec(viol, p):
    n, x = len(viol), int(viol.sum())
    ph = min(max(x / n, 1e-12), 1 - 1e-12)
    ll = lambda q: (n - x) * np.log(1 - q) + x * np.log(q)
    lr = -2 * (ll(p) - ll(ph))
    return x, n, lr, 1 - stats.chi2.cdf(lr, 1)


def christoffersen_ind(viol):
    v = np.asarray(viol).astype(int)
    n00, n01 = ((v[:-1] == 0) & (v[1:] == 0)).sum(), ((v[:-1] == 0) & (v[1:] == 1)).sum()
    n10, n11 = ((v[:-1] == 1) & (v[1:] == 0)).sum(), ((v[:-1] == 1) & (v[1:] == 1)).sum()
    if min(n01 + n11, n00 + n01, n10 + n11) == 0:
        return np.nan
    pi01, pi11, pi = n01 / (n00 + n01), n11 / (n10 + n11), (n01 + n11) / len(v[1:])
    ll = lambda q, k, t: k * np.log(q) + (t - k) * np.log(1 - q)
    lr = -2 * (ll(pi, n01 + n11, len(v) - 1) - ll(pi01, n01, n00 + n01) - ll(pi11, n11, n10 + n11))
    return 1 - stats.chi2.cdf(lr, 1)


def block_bootstrap_sharpe(E, B=3000, L=20, seed=5209):
    """E: DataFrame of daily EXCESS returns, column 0 = strategy. Stationary block bootstrap (mean block L).
    Returns draws of Sharpe for every column."""
    rng, V, n = np.random.default_rng(seed), E.values, len(E)
    sh = lambda x: x.mean(0) / x.std(0) * np.sqrt(TRADING_DAYS)
    out = np.empty((B, V.shape[1]))
    for b in range(B):
        o, i = np.empty(n, int), 0
        while i < n:
            st, ln = rng.integers(n), min(rng.geometric(1 / L), n - i)
            o[i:i + ln] = (st + np.arange(ln)) % n
            i += ln
        out[b] = sh(V[o])
    return out, sh(V)
