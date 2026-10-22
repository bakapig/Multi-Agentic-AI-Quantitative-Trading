# NDX momentum-hedge strategy (replication of `ndx-momentum-hedge-main`)

Every 5 trading days, at the close: keep Nasdaq-100 names with 20-day momentum > 0, rank by 5-day momentum, hold the top 5 equal-weight
(50% of capital) and put the other 50% in PSQ (1x inverse QQQ). Paper only: nothing here places orders. Not connected to `fund_agents`.
Frozen parameters live in `config.py` and must not be retuned after 2026-10-01.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-momentum.txt     # no new dependencies
.\.venv\Scripts\python.exe scripts\run_ndx_momentum_backtest.py      # weekly backtests on the cached snapshot -> reports/ndx_momentum/
.\.venv\Scripts\python.exe scripts\run_ndx_momentum_daily.py         # daily update (network) -> live/ndx_momentum/
.\.venv\Scripts\python.exe -m unittest tests.test_ndx_momentum -v
```

| File | Role |
|---|---|
| `config.py` | Rule parameters, the repo's hard-coded `NDX_100` list, variants, output paths |
| `universe.py` | `static` list and point-in-time membership `PIT` (port of the repo's `pit_universe.py`) |
| `data.py` | yfinance adjusted closes, snapshot `data/ndx_momentum/prices.csv.gz`, membership files beside it |
| `strategy.py` | Selection rule, weekly backtest (repo engines), daily returns for a window, current book |
| `live.py` | Daily update: pinned history, completed bars only, drift report, outputs below |
| `research/ndx_sgx/` | Research study, not part of the daily update: the same rule with SGX (STI) stocks added to the universe (see below) |

## Variants reported every day
| Name | Universe | Fill | Cost | Purpose |
|---|---|---|---|---|
| `pit_next_close_10bp` (primary) | point-in-time members, one share class per company | next close | 10 bp one-way on stock turnover | closest to something tradable |
| `static_repo_signal_close_0bp` | the repo's hard-coded list | signal close | none | what the repo's own engine reports |

## Evidence on the cached snapshot (2021-06-07 to 2026-08-06, 255 weekly trades; `reports/ndx_momentum/performance.csv`)
| | Total | CAGR | Sharpe (rf = 0) | Max drawdown |
|---|---|---|---|---|
| Static list, signal-close fill, 0 bp (repo) | +111.4% | 15.9% | 1.27 | -12.8% |
| Static list, next-close fill, 10 bp | +49.8% | 8.3% | 0.74 | -20.5% |
| Point-in-time, signal-close fill, 0 bp | +33.2% | 5.8% | 0.57 | -17.1% |
| **Point-in-time, next-close fill, 10 bp (primary)** | **-5.2%** | **-1.1%** | **-0.03** | **-25.1%** |
| QQQ buy-and-hold | +107.1% | 15.4% | 0.78 | -33.7% |

The static list matches the repo's published figures and carries hindsight bias: it includes names that joined the index after large runs.
Extended to the last bar (2026-10-20) the point-in-time results fall further (signal-close 0 bp +14.4%, primary -7.6%) because the
August to September picks included recently added, volatile names (CRWV, NBIS, SNDK, SPCX) that are not in the static list.
Treat the primary variant as the strategy; the static variant is a reference.

## Research: SGX assets added to the rule (`research/ndx_sgx/`)
`python ndx_momentum/research/ndx_sgx/ndx_sgx.py` runs the same rule on six universes: current NDX members, point-in-time NDX members, the 29 current STI names, two
pooled NDX + SGX rankings and a 50/50 two-sleeve book. Each pick is hedged with its own index (QQQ for US names, ES3.SI for SGX names), so the book is currency-neutral.
Fills are at the next close with 10 bp (US) and 25 bp (SGX) per side. It reads the cached prices and membership inputs in its own `data/` folder and writes `results/`.

| 2017-06 to 2026-10, net of costs | Excess return / yr | Sharpe |
|---|---|---|
| NDX current members (hindsight) | +2.0% | 0.31 |
| NDX point-in-time members | -2.0% | -0.32 |
| SGX only (STI current members) | -3.9% | -1.10 |
| Pooled NDX + SGX, raw 5d rank | -1.8% | -0.20 |
| Pooled, volatility-normalised rank | -4.4% | -0.72 |
| Two sleeves 50/50 | -0.9% | -0.21 |

SGX names add nothing here, and a random-pick placebo finds no ranking skill in the SGX universe (p = 0.68). The study is therefore kept as research and is not a live variant.

## Daily outputs (`live/ndx_momentum/`)
| File | Content |
|---|---|
| `daily_picks.csv` | One row per pick and variant per as-of date: decision date, fill date, weight, 5d and 20d momentum, price. PSQ appears as the hedge row |
| `test_period_returns.csv` | Daily returns from 2026-10-01 for each variant and QQQ (weights treated as rebalanced daily inside the week) |
| `portfolio_closing_prices.csv` | Daily adjusted closes from 2026-10-01 of every name picked, QQQ and PSQ |
| `portfolio_kpis.json` | Window statistics per variant: cumulative return, volatility, Sharpe (rf = 0), max drawdown |
| `run_manifest.json` | Last close, drift report, unavailable tickers, membership anchor, `orders_enabled: false`, config hash |

## Data rules
- History up to 2026-09-30 is pinned to the snapshot. Later rows come from Yahoo, rescaled onto the snapshot's adjustment basis.
- Only completed bars are used: dates on or after today's UTC date are dropped, and the panel ends at the last date with both QQQ and PSQ.
- The weekly grid is anchored at 2021-06-07 on the QQQ calendar, so rebalance days are fixed by the data.
- Membership is anchored at 2026-10-15 (`ndx_constituents_anchor.csv`, `ndx_changes.csv`). A later index change needs a new row in `ndx_changes.csv` and a new anchor.
- Eleven former members have no Yahoo history and can never be picked (ALXN, ANSS, ATVI, CERN, EA, MXIM, SGEN, SPLK, WBA, WBD, XLNX), so some bias remains.

## Not implemented
- Backpack Exchange tradability filter used by the repo's live dashboard.
- The dashboard's 19-day "20-day momentum" definition: this package uses a true 20-day return, as the repo's backtests do.
- Connection to the fund risk layer (see `ARCHITECTURE.md`: the fund models two-leg pair groups with an 80% gross cap, while this book holds a single-leg 50% stock sleeve and a PSQ hedge).
