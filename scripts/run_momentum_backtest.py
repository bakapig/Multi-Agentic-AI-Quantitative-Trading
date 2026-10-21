"""Full evaluation of the frozen strategy: performance vs corrected benchmarks, bootstrap, factor regression (L3), VaR/ES backtest (L7),
stationarity (L5), brief metrics, live test window. Usage: python scripts/run_momentum_backtest.py"""
import sys, warnings; warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.tsa.stattools import adfuller, kpss
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from momentum.config import *
from momentum.data import download, weekday_panel, rf_daily
from momentum.strategy import garch_vol_forecasts, run_blend, trade_log
from momentum.garch import fit, filter_h
from momentum.metrics import summary, drawdown, kupiec, christoffersen_ind, block_bootstrap_sharpe

px, irx = download()
raw, ff = weekday_panel(px)
rf = rf_daily(irx, ff.index)
gv = garch_vol_forecasts(raw, DATA / "garch_vol_forecasts.csv")
R = run_blend(ff, gv, rf)
r = ff.pct_change().fillna(0.0)
S0 = pd.Timestamp(EVAL_START)

# ---- L5: stationarity of the original 10 assets
rows = []
for c in raw.columns:
    lp = np.log(raw[c].dropna()); d = lp.diff().dropna()
    rows.append(dict(asset=c, adf_p_logprice=adfuller(lp, autolag="AIC")[1], kpss_p_logprice=kpss(lp, nlags="auto")[1],
                     adf_p_return=adfuller(d, autolag="AIC")[1], kpss_p_return=kpss(d, nlags="auto")[1]))
pd.DataFrame(rows).round(4).to_csv(RES / "stationarity_L5.csv", index=False)

# ---- benchmarks (all on the same daily grid; strategy figures are after costs and financing)
fin_of = lambda g: (g - 1).clip(lower=0) * (rf + FIN_SPREAD / TRADING_DAYS)
b6040 = 0.6 * r["SPY"] + 0.4 * r["IEF"]
k = (0.082 / (b6040.rolling(60).std().shift(1) * np.sqrt(TRADING_DAYS))).clip(upper=2.0).fillna(1.0)   # ex-ante leverage; 8.2% = blend's realised vol level
b6040_vt = k * b6040 + (1 - k).clip(lower=0) * rf - fin_of(k)
ew = r.where(raw.notna().cumsum() > GARCH_MIN_OBS).mean(axis=1)
S = pd.DataFrame({"BLEND 50/50": R["net"], "Core sleeve": R["core"], "Trend sleeve": R["trend"], "EW buy&hold same 21": ew,
                  "60/40 SPY/IEF": b6040, "60/40 vol-targeted": b6040_vt, "SPY (reference)": r["SPY"]}).loc[S0:].dropna()

periods = {"full": (None, None), "validation<=2023-09": (None, VALIDATION_END), "seen 2023-10..2026-09": ("2023-10-01", SEEN_END),
           "2008-09": ("2008-01-01", "2009-12-31"), "2022": ("2022-01-01", "2022-12-31")}
rows = [{**summary(S[n].loc[a:b], rf).to_dict(), "period": p, "strategy": n} for p, (a, b) in periods.items() for n in S]
T = pd.DataFrame(rows).round(3)
T.to_csv(RES / "performance_vs_benchmarks.csv", index=False)
pd.set_option("display.width", 250)
for c in ["ann_return", "ann_vol", "sharpe_ex_rf", "max_dd"]:
    print("\n" + c + "\n", T.pivot(index="strategy", columns="period", values=c).reindex(list(S)).to_string())

# ---- bootstrap: blend minus each benchmark (Sharpe, excess of rf)
E = S.sub(rf.loc[S.index], axis=0)
draws, pt = block_bootstrap_sharpe(E)
BS = pd.DataFrame([dict(benchmark=n, sharpe_blend=pt[0], sharpe_bench=pt[j], diff=pt[0] - pt[j], ci_lo=np.percentile(draws[:, 0] - draws[:, j], 2.5),
                        ci_hi=np.percentile(draws[:, 0] - draws[:, j], 97.5)) for j, n in enumerate(S.columns) if j > 0]).round(3)
BS.to_csv(RES / "bootstrap_sharpe_diff.csv", index=False)
print("\nBootstrap Sharpe difference (blend minus benchmark)\n", BS.to_string(index=False))

# ---- L3: factor regression on SPY and IEF excess returns, Newey-West
X = sm.add_constant(pd.DataFrame({"SPY": r["SPY"] - rf, "IEF": r["IEF"] - rf}).loc[S.index])
reg = []
for n in ["BLEND 50/50", "Core sleeve", "Trend sleeve"]:
    m = sm.OLS(E[n], X).fit(cov_type="HAC", cov_kwds={"maxlags": 10})
    reg.append(dict(strategy=n, alpha_ann=m.params["const"] * TRADING_DAYS, alpha_t=m.tvalues["const"], beta_SPY=m.params["SPY"], beta_IEF=m.params["IEF"], r2=m.rsquared))
REG = pd.DataFrame(reg).round(3); REG.to_csv(RES / "factor_regression.csv", index=False)
print("\nFactor regression\n", REG.to_string(index=False))

# ---- brief metrics for the blend (win rate, trades, holding period, profit/trade need the trade log of the lagged book)
tr = trade_log(R["Wlag"].loc[S0:], ff)
BR = pd.DataFrame({p: summary(R["net"].loc[a:b].loc[S0:], rf, tr, R["turn"]) for p, (a, b) in periods.items()}).T.round(4)
BR.to_csv(RES / "brief_metrics_blend.csv"); print("\nBrief metrics (blend)\n", BR.T.to_string())
tr.to_csv(RES / "trades.csv", index=False)

# ---- L7: VaR/ES backtest of the blend: GARCH-t and filtered historical simulation (GJR-t filter, empirical quantile of last 1000 residuals)
v = 100 * R["net"].loc[S0:]; vv, n = v.values, len(v)
out = []
for model in ["GARCH-t", "FHS (GJR)"]:
    sg, nu, zq = np.full(n, np.nan), np.full(n, np.nan), {0.99: np.full(n, np.nan), 0.95: np.full(n, np.nan)}
    par = None
    for s in range(500, n, REFIT_EVERY):
        lo, e = max(0, s - GARCH_WINDOW), min(n, s + REFIT_EVERY)
        par = fit(vv[lo:s + 1], par, gjr=(model != "GARCH-t"))
        h = filter_h(vv[lo:e], par[0], par[1], par[2], par[4] if len(par) == 5 else 0.0)
        sg[s:e], nu[s:e] = np.sqrt(h[s + 1 - lo:e + 1 - lo]) / 100, par[3]
        if model.startswith("FHS"):
            z = vv[lo:s + 1] / np.sqrt(h[:s + 1 - lo])
            for a in zq:
                zq[a][s:e] = -np.quantile(z[-1000:], 1 - a)
    sgS, nuS = pd.Series(sg, v.index).shift(1), pd.Series(nu, v.index).shift(1)       # forecast known at close t-1 for the loss at t
    for a in [0.99, 0.95]:
        q = pd.Series(zq[a], v.index).shift(1) if model.startswith("FHS") else stats.t.ppf(a, nuS) * np.sqrt((nuS - 2) / nuS)
        lim = sgS * q; m = lim.notna()
        viol = (-R["net"].loc[S0:][m] > lim[m]).astype(int)
        x, nn, lr, p = kupiec(viol, 1 - a)
        out.append(dict(model=model, level=a, viol_rate=x / nn, kupiec_p=p, christoffersen_p=christoffersen_ind(viol.values)))
VAR = pd.DataFrame(out).round(4); VAR.to_csv(RES / "var_backtest.csv", index=False)
print("\nVaR backtest\n", VAR.to_string(index=False))

# ---- plots / saved series
fig, ax = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
(1 + S[["BLEND 50/50", "Core sleeve", "Trend sleeve", "60/40 vol-targeted", "EW buy&hold same 21", "SPY (reference)"]]).cumprod().plot(ax=ax[0], logy=True)
ax[0].axvline(pd.Timestamp("2023-10-01"), ls="--", c="k"); ax[0].set_title("Net of costs and financing (dashed = start of already-inspected window)")
drawdown(S["BLEND 50/50"]).plot(ax=ax[1], title="Blend drawdown"); plt.tight_layout(); plt.savefig(RES / "equity_drawdown.png", dpi=110)
S.to_csv(RES / "daily_returns.csv"); R["W"].to_csv(RES / "weights_blend.csv")
