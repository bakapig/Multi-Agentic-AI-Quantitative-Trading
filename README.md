# Meridian Ensemble Research System

One Ensemble PM combines the teammate's **trend following, momentum and mean
reversion** engines. Independent fund risk approves portfolio targets, and an
advisory evidence lane reviews the results. The standalone Kalman/OU Pairs PM
has been removed from the active code.

The illustrative USD 5 million mandate is USD 3 million for the ensemble and
USD 2 million central cash. The prototype records intentions with **zero fills**.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-fund.txt
.\.venv\Scripts\python.exe -m fund_agents
.\.venv\Scripts\python.exe -m fund_agents.dashboard
```

Open <http://127.0.0.1:8765> to inspect the three engines, actual allocation weights,
fund risk, Phantom Book, committee evidence, system flow and decision ledger.
Current reports use `ensemble-fund-v3`; earlier report schemas are historical.

- [Current architecture](ARCHITECTURE.md)
- [Updated slide diagram](presentations/architecture_20261020/ensemble_architecture.html)
- [Architecture PDF](output/pdf/Ensemble_Fund_Architecture_20261020.pdf)
- [Fund run guide and account schema](fund_agents/README.md)
- [Standalone ensemble research](multi_strategy_ensemble/README.md)
- [Presentation index](presentations/README.md)
- [NDX momentum-hedge strategy (top-5 momentum stocks + PSQ hedge, point-in-time universe)](ndx_momentum/README.md):
  separate paper strategy with its own daily update (`scripts/run_ndx_momentum_daily.py`) and outputs in `live/ndx_momentum/` and
  `reports/ndx_momentum/`. It is not connected to `fund_agents`.

The default regime policy currently gives mean reversion 0% in every state.
Equal-weight and inverse-volatility policies include all three engines. The
connected adapter currently uses an explicit USD US-equity universe with XNYS
sessions. Automatic LLM calls, fills and consolidated fund returns remain pending.

## October 1–20, 2026 backtests

Compare the original Backtrader ensemble with the newly added standalone momentum
strategy in [the October report](reports/october_2026/research_report.md) or
[the browser results page](reports/october_2026/index.html).
All variants, daily returns, weights, data exclusions and source hashes are saved.

The full original universe contains 878 assets, and the new momentum universe
contains 20 assets. Both cover all 14 test sessions. Missing final daily bars were
recovered from dated closing quote snapshots and a checked end-of-day source;
the report records the exact marks, timestamps, scale factors and limitations.
No asset was dropped and no missing October 20 close was carried forward.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/refresh_ensemble_prices.py --end 2026-10-20
.\.venv\Scripts\python.exe scripts/compare_october_strategies.py
```

These are research simulations with different universes, execution rules and
starting-position conventions. They are separate from the fund's intention-only
adapter and do not establish consolidated fund returns. Read the report's method
notes before comparing the results. Parameters were not optimized on October.

## Standalone momentum strategy

The [momentum module](momentum/README.md) combines a 50% time-series trend sleeve
and a 50% long-only inverse-volatility core, using walk-forward GARCH-t volatility
forecasts. Its current 20 assets include US-listed funds and four SGX securities.
The portfolio targets 10% annual volatility with a 3x gross exposure cap, applies
its original lag of two bars, and models trading costs and financing.

```powershell
.\.venv\Scripts\python.exe scripts/run_momentum_daily.py --no-refresh --as-of-utc 2026-10-21
.\.venv\Scripts\python.exe scripts/run_momentum_backtest.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The daily updater writes to `live/momentum/`; the full historical evaluation
writes to `reports/momentum/`. No scheduler is installed by these commands.

## Project scope

The active project contains the equity ensemble, standalone multi-asset momentum,
shared utilities and the fund dashboard. Removed legacy experiments, data and
presentation exports have been moved outside this working tree to a recoverable
local archive. Git history is preserved. Existing local fund-integration changes
are retained.
