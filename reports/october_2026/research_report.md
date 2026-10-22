# AlphaHunt Capital — ensemble research

2026-10-01 through 2026-10-20, 14 trading sessions. Percentage returns; normalized index starts at 100.

| strategy                    |   total_return_pct |   max_drawdown_pct |   annualized_sharpe |
|:----------------------------|-------------------:|-------------------:|--------------------:|
| Dynamic ensemble            |              4.485 |             -1.165 |               6.763 |
| Equal-weight ensemble       |              2.625 |             -0.421 |               8.534 |
| Inverse-volatility ensemble |              2.625 |             -0.421 |               8.534 |
| Trend following             |              2.655 |             -0.748 |               7.741 |
| Momentum                    |              5.250 |             -1.491 |               6.372 |
| Mean reversion              |             -0.006 |             -0.183 |              -7.569 |
| SPY benchmark               |              0.842 |             -2.033 |               1.221 |

![Ensemble backtest](comparison.png)

The research universe contains 878 global assets. The connected account adapter separately uses 14 US equities. These results are standalone research, not actual fund NAV performance.

- Research simulations; the account adapter records intentions and has no confirmed fills.
- Market-specific commissions, board lots, short borrow and modeled 2 bp slippage.
- Same-close execution and synthetic high/low bars are optimistic execution assumptions.
- Regime allocations use the prior session. The current policy assigns mean reversion zero weight.
- Local-currency asset returns have no FX conversion model. These are not reconciled fund returns.
- The 14-session sample is too short to establish persistent risk-adjusted performance.
- The proposed intraday and 7% halt profile was not applied to this historical backtest.

Reproduce with `python scripts/run_ensemble_backtest.py --start 2026-10-01 --end 2026-10-20`.
