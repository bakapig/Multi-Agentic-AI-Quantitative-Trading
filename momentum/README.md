# Momentum strategy: 50% trend + 50% risk-parity core, GARCH(1,1)-t volatility targeting

21 liquid assets (including four SGX names and BTC-USD), long/short trend sleeve plus long-only risk-parity core, volatility-targeted
with walk-forward GARCH-t forecasts (FE5209 L6). Frozen parameters live in `config.py` and must not be retuned after 2026-10-01.
Paper only: nothing here places orders.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-momentum.txt
.\.venv\Scripts\python.exe scripts\run_momentum_backtest.py     # full evaluation -> reports/momentum/
.\.venv\Scripts\python.exe scripts\run_momentum_daily.py        # daily update -> live/momentum/
.\.venv\Scripts\python.exe -m unittest tests.test_momentum_strategy -v
```

| File | Role |
|---|---|
| `config.py` | Assets (21), costs, lookbacks, targets, split dates, output paths |
| `data.py` | yfinance adjusted closes + ^IRX, cached in `data/momentum/` |
| `garch.py` | GARCH-t / GJR-GARCH-t maximum likelihood (L6) |
| `strategy.py` | Walk-forward GARCH vol forecasts (full and incremental), trend signal, vol-targeted weights, throttle, backtest, `run_blend` |
| `metrics.py` | Brief metrics, Kupiec/Christoffersen (L7), block bootstrap |
| `live.py` | Daily update (see below) |
| `scripts/run_momentum_backtest.py` | Benchmarks, bootstrap, factor regression (L3), VaR backtest (L7), stationarity (L5), plots. Writes `reports/momentum/` |
| `scripts/run_momentum_daily.py`, `.ps1`, `install_momentum_daily_task.ps1` | Daily update runner and Windows scheduler |

Execution assumption: signal at close t, fill at close t+1 (lag 2). Returns are after trading costs and, for the blend, financing
(rf + 50 bp on gross above 1x NAV). Sharpe ratios are on excess returns over the 13-week T-bill.

## Daily update (`live.py`)

1. Fetch Yahoo daily bars. History up to 2026-09-30 is pinned to the cached snapshot (`data/momentum/prices.csv`); later rows come from
   the fetch, rescaled onto the snapshot's adjustment basis, and a bar Yahoo fails to return keeps its cached value.
2. Keep completed bars only: drop dates on or after today's UTC date, then end the panel at the last date on which SPY, D05.SI and
   BTC-USD all have a bar (Yahoo can omit bars around the UTC rollover; an omitted bar would otherwise be forward-filled as a zero return).
3. Report any Yahoo revision of the pinned history (daily log return difference above 1e-5) in `run_manifest.json`. The snapshot is kept.
4. Extend the GARCH-t forecasts from each asset's last refit block using the stored parameters (`data/momentum/garch_state.json`). It
   refits only at new 63-observation blocks and equals a full refit up to the block's initial-variance start value. `--full-refit`
   rebuilds everything (about 20 seconds).
5. Run `run_blend` and write the outputs below. Orders would fill at the next close.

| Output (`live/momentum/`) | Content |
|---|---|
| `portfolio_closing_prices.csv` | Daily adjusted closes of all 21 assets from 2026-10-01 (own calendars, no filling) |
| `assets.csv` | Asset list, sleeve group, market |
| `daily_weights.csv` | Target weights as fractions of NAV (negative = short), one row per as-of date |
| `test_period_returns.csv` | Net daily returns in the test window |
| `portfolio_kpis.json` | Brief metrics for the test window |
| `run_manifest.json` | Last close, GARCH mode, history drift, `orders_enabled: false`, config hash |

`reports/momentum/PARAMETER_MANIFEST.json` records the frozen parameters and the hash of `config.py`.

`tests/test_momentum_strategy.py` checks that the packaged strategy reproduces the original research returns on the frozen history to
1e-10, that weights never depend on future prices, that incremental GARCH equals a full refit, and the completed-bar and drift rules.
