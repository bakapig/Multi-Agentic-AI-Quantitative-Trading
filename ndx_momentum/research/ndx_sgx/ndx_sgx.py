"""NDX momentum-hedge rule (20d>0 filter, rank by 5d momentum, top 5, weekly) re-tested with SGX (STI) assets wired in.
Questions: (1) does the hindsight-biased edge survive realistic execution/costs, (2) how much of it is the universe (current vs point-in-time
members; random-pick placebo), (3) do SGX names add anything, alone or pooled with NDX?
Each pick is hedged with its own market index (QQQ for US names, ES3.SI for SGX names), so the book is dollar-neutral on the index leg and
currency-neutral by construction (stock and its hedge share a currency). Excess return over cash = sum_i w_i (r_i - r_index(i)).
Execution: decide at close t, fill at close t+1 (lag 2 in the main package), 10 bp US / 25 bp SGX per side, 1 bp on hedge turnover.
Research only, not part of the daily ndx_momentum update: reads data/inputs and the cached data/prices.csv.gz (re-downloaded from Yahoo if absent),
writes results/. Not imported by ndx_momentum or momentum.
Usage: python ndx_momentum/research/ndx_sgx/ndx_sgx.py"""
import warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, yfinance as yf
import statsmodels.api as sm

HERE = Path(__file__).parent
SRC = HERE / "data" / "inputs"
DATA, RES = HERE / "data", HERE / "results"
DATA.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)

START, K, W_STOCK, EVERY, LAG = "2015-06-01", 5, 0.5, 5, 2
LOOK, RANK = 20, 5
COST = dict(US=10e-4, SG=25e-4, HEDGE=1e-4)
WINDOWS = {"2017-06..2026-10": "2017-06-01", "2021-01..2026-10": "2021-01-04"}
DROP = {"GOOG", "FOX", "LBTYK", "LILAK", "NWSA", "DISCK"}       # one share class per company
rng = np.random.default_rng(5209)

cur = pd.read_csv(SRC / "nasdaq100_current.csv")
pit = pd.read_csv(SRC / "nasdaq100_pit_membership.csv", parse_dates=["start_date", "end_date"])
sti = pd.read_csv(SRC / "sti_current.csv")["ticker"].tolist()
ndx_cur = [t for t in cur.ticker if t not in DROP]
pit = pit[~pit.ticker.isin(DROP) & (pit.end_date.isna() | (pit.end_date >= "2016-01-01"))]


def download():
    f = DATA / "prices.csv.gz"
    if f.exists():
        return pd.read_csv(f, index_col=0, parse_dates=True)
    tk = sorted(set(ndx_cur) | set(pit.ticker) | set(sti) | {"QQQ", "ES3.SI"})
    parts = []
    for i in range(0, len(tk), 40):
        p = yf.download(tk[i:i + 40], start=START, auto_adjust=True, progress=False)["Close"]
        parts.append(p if isinstance(p, pd.DataFrame) else p.to_frame(tk[i]))
    px = pd.concat(parts, axis=1).dropna(how="all")
    px.to_csv(f)
    return px


px = download()
cal = pd.bdate_range(px.index.min(), px.index.max())
raw = px.reindex(cal); ff = raw.ffill(limit=5)
ret = ff.pct_change()
mom_l, mom_r = ff / ff.shift(LOOK) - 1, ff / ff.shift(RANK) - 1
sd60 = ret.rolling(60).std()
traded = raw.notna() & raw.notna().rolling(LOOK + 1).sum().ge(LOOK + 1)
sg = [t for t in sti if t in px.columns and px[t].notna().sum() > 300]
us_cur = [t for t in ndx_cur if t in px.columns]
us_pit_all = [t for t in pit.ticker.unique() if t in px.columns]
print(f"prices: {px.shape}; NDX current with data {len(us_cur)}/{len(ndx_cur)}; PIT tickers with data {len(us_pit_all)}/{pit.ticker.nunique()}; STI with data {len(sg)}/{len(sti)}")
print("calendar", cal[0].date(), cal[-1].date())


def pit_members(t):
    m = pit[(pit.start_date <= t) & (pit.end_date.isna() | (t < pit.end_date))]
    return [x for x in m.ticker if x in px.columns]


def pick(t, pool, key, k=K):
    """top-k of pool by key among names that traded today with positive 20d momentum, known at close t."""
    c = [x for x in pool if traded.at[t, x] and mom_l.at[t, x] > 0 and np.isfinite(key.at[t, x])]
    return sorted(c, key=lambda x: -key.at[t, x])[:k]


def idx_of(tk):
    return "ES3.SI" if tk.endswith(".SI") else "QQQ"


rebal = [i for i in range(LOOK + 60, len(cal)) if i % EVERY == 0]
REBAL = set(rebal)


def weights(rule):
    """Daily weight matrices (stocks N, hedge on QQQ/ES3.SI) decided at close t, held until the next rebalance."""
    cols = sorted(set(us_cur) | set(us_pit_all) | set(sg)); W = pd.DataFrame(0.0, index=cal, columns=cols)
    H = pd.DataFrame(0.0, index=cal, columns=["QQQ", "ES3.SI"])
    cur_w, cur_h = pd.Series(0.0, index=cols), pd.Series(0.0, index=H.columns)
    picks = {}
    for i, t in enumerate(cal):
        if i in REBAL:
            if rule == "NDX current":                p = pick(t, us_cur, mom_r)
            elif rule == "NDX point-in-time":        p = pick(t, pit_members(t), mom_r)
            elif rule == "SGX only (STI current)":   p = pick(t, sg, mom_r)
            elif rule == "Pooled NDX+SGX, raw 5d rank":   p = pick(t, us_cur + sg, mom_r)
            elif rule == "Pooled NDX+SGX, vol-norm rank": p = pick(t, us_cur + sg, mom_r / sd60)
            elif rule == "Two sleeves 50/50 (NDX top5 + SGX top5)": p = pick(t, us_cur, mom_r) + pick(t, sg, mom_r)
            ws = np.full(len(p), (W_STOCK / K) * (0.5 if rule.startswith("Two") else 1.0))
            cur_w = pd.Series(0.0, index=cols); cur_h = pd.Series(0.0, index=H.columns)
            for x, w in zip(p, ws):
                cur_w[x] += w; cur_h[idx_of(x)] += w
            picks[t] = p
        W.iloc[i], H.iloc[i] = cur_w.values, cur_h.values
    return W, H, picks


def run(rule):
    W, H, picks = weights(rule)
    Wl, Hl = W.shift(LAG).fillna(0), H.shift(LAG).fillna(0)
    r_s, r_h = ret[W.columns].fillna(0), ret[H.columns].fillna(0)
    gross = (Wl * r_s).sum(1) - (Hl * r_h).sum(1)
    tw = Wl.diff().abs().fillna(0)
    cost = (tw * np.array([COST["SG"] if c.endswith(".SI") else COST["US"] for c in W.columns])).sum(1) + Hl.diff().abs().fillna(0).sum(1) * COST["HEDGE"]
    return gross, gross - cost, tw.sum(1), picks


def stats(x, turn=None):
    x = x.dropna(); eq = (1 + x).cumprod()
    d = dict(ann_excess=(1 + x).prod() ** (252 / len(x)) - 1, vol=x.std() * np.sqrt(252), sharpe=x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else np.nan, mdd=(eq / eq.cummax() - 1).min())
    if turn is not None:
        d["wk_turnover"] = turn.loc[x.index].sum() / (len(x) / 5)
    return d


def tstat(g):
    wk = (1 + g).resample("W-FRI").prod() - 1
    m = sm.OLS(wk.values, np.ones(len(wk))).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    return m.params[0] * 52, m.tvalues[0]


rules = ["NDX current", "NDX point-in-time", "SGX only (STI current)", "Pooled NDX+SGX, raw 5d rank", "Pooled NDX+SGX, vol-norm rank", "Two sleeves 50/50 (NDX top5 + SGX top5)"]
rows, series, allpicks = [], {}, {}
for rl in rules:
    g, n, tn, pk = run(rl); series[rl] = (g, n); allpicks[rl] = pk
    for wn, w0 in WINDOWS.items():
        gs, ns = g.loc[w0:], n.loc[w0:]
        a, t = tstat(gs)
        rows.append(dict(rule=rl, window=wn, **{f"net_{k}": v for k, v in stats(ns, tn).items()}, gross_ann_excess=stats(gs)["ann_excess"], gross_t=t,
                         share_sgx_picks=np.mean([p.endswith(".SI") for ps in pk.values() for p in ps]) if pk else np.nan))
R = pd.DataFrame(rows).round(3); R.to_csv(RES / "ndx_sgx_results.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 20)
for wn in WINDOWS:
    print(f"\n=== {wn}: excess return over cash (stock sleeve 50% minus index hedge), lag 2, costs ===")
    print(R[R.window == wn].drop(columns="window").to_string(index=False))

# benchmark: hold equal-weight basket of current NDX members hedged with QQQ (is the "top-5" even better than the average member?) and the placebo
w0 = WINDOWS["2017-06..2026-10"]
rb = [i for i in rebal if cal[i] >= pd.Timestamp(w0) - pd.Timedelta(days=10)]


def period_returns(pool_fn, key):
    """For every rebalance date: candidate pool, and holding-period (lag-adjusted) returns of each name and of its hedge index."""
    out = []
    for i in rb:
        if i + LAG + EVERY >= len(cal):
            break
        t = cal[i]; c = [x for x in pool_fn(t) if traded.at[t, x] and mom_l.at[t, x] > 0 and np.isfinite(key.at[t, x])]
        a, b = i + LAG - 1, i + LAG - 1 + EVERY                          # entry at close of day i+1, exit at close of day i+1+EVERY
        pr = {x: ff.iloc[b][x] / ff.iloc[a][x] - 1 for x in c if np.isfinite(ff.iloc[b][x] / ff.iloc[a][x] - 1)}
        pi = {k: ff.iloc[b][k] / ff.iloc[a][k] - 1 for k in ["QQQ", "ES3.SI"]}
        out.append((t, c, pr, pi))
    return out


def realised(per, key):
    ex = []
    for t, c, pr, pi in per:
        ps = [x for x in sorted(pr, key=lambda x: -key.at[t, x])[:K]]
        ex.append(np.mean([pr[x] - pi[idx_of(x)] for x in ps]) * W_STOCK if ps else 0.0)
    return np.array(ex)


def placebo(per, B=2000):
    out = np.empty(B)
    for b in range(B):
        ex = []
        for t, c, pr, pi in per:
            names = list(pr)
            if not names:
                ex.append(0.0); continue
            ps = rng.choice(names, size=min(K, len(names)), replace=False)
            ex.append(np.mean([pr[x] - pi[idx_of(x)] for x in ps]) * W_STOCK)
        out[b] = np.mean(ex) * 252 / EVERY
    return out


print("\n=== Placebo: does ranking by 5d momentum add anything beyond the universe? (gross excess per year, 2017-06 on, no costs) ===")
pl_rows = []
for name, pool_fn, key in [("NDX current", lambda t: us_cur, mom_r), ("NDX point-in-time", pit_members, mom_r), ("SGX only (STI current)", lambda t: sg, mom_r)]:
    per = period_returns(pool_fn, key)
    real = realised(per, key).mean() * 252 / EVERY
    allavg = np.mean([np.mean([pr[x] - pi[idx_of(x)] for x in pr]) * W_STOCK if pr else 0.0 for t, c, pr, pi in per]) * 252 / EVERY
    pb = placebo(per, 1000)
    pl_rows.append(dict(universe=name, rebalances=len(per), strategy_gross=real, all_positive20d_names=allavg, random5_mean=pb.mean(), random5_p95=np.percentile(pb, 95),
                        p_value_rank_skill=(pb >= real).mean()))
PL = pd.DataFrame(pl_rows).round(3); PL.to_csv(RES / "placebo.csv", index=False); print(PL.to_string(index=False))

# year-by-year net for the main rules
yr = pd.DataFrame({rl: series[rl][1].loc[w0:].groupby(series[rl][1].loc[w0:].index.year).apply(lambda s: (1 + s).prod() - 1) for rl in rules}).round(3)
yr.to_csv(RES / "by_year.csv"); print("\nNet excess return by year\n", yr.to_string())
pd.DataFrame({rl: series[rl][1] for rl in rules}).to_csv(RES / "daily_net_excess.csv")
for rl, pk in allpicks.items():
    pd.Series({str(t.date()): ",".join(p) for t, p in pk.items()}, name="picks").to_csv(RES / ("picks_" + "".join(ch if ch.isalnum() else "_" for ch in rl) + ".csv"))
