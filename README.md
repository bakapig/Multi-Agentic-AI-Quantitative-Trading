# AlphaHunt Capital

Presented by **alphahunter**. An absolute-return, systematic quantitative research
fund built around one ensemble, independent risk and a two-lane architecture.
The objective is equity participation with a more defensive risk experience.

## Investor dashboard

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m fund_agents.dashboard
```

Open <http://127.0.0.1:8765/>. The investor view shows percentage performance,
normalized backtest curves, ensemble allocations, a percentage-based Phantom Book,
and governance status. It does not disclose account capital, balances, units or
dollar exposures. Raw account-report endpoints are not served.

## Ensemble backtesting — October 1–20, 2026

```powershell
.\.venv\Scripts\python.exe scripts/run_ensemble_backtest.py --start 2026-10-01 --end 2026-10-20
```

Outputs are in [reports/october_2026](reports/october_2026/research_report.md).
The compatibility command `scripts/compare_october_strategies.py` now invokes this
same ensemble-only runner. The active workflow includes trend following, momentum,
mean reversion, ensemble allocation variants and SPY. Separate historical research
packages do not feed the investor dashboard or this backtest runner.

The original research universe contains 878 global assets. The connected account
adapter separately supports a declared 14-name US-equity universe. Standalone
research returns are not consolidated fund NAV or confirmed trading results.
The default regime policy allocates 0% to mean reversion; equal-weight and
inverse-volatility alternatives include it. The crisis policy holds 70% of the
trading sleeve in cash.

## Risk and advisory status

The proposed AlphaHunt investor profile is a 2.5% intraday halt and a 7% persistent
maximum-drawdown halt pending human review. It is **not implemented or applied to
the October backtest**. The saved account policy retains its 12% soft threshold
and 25% hard breaker. Intraday monitoring and execution handling remain pending.
No halt guarantees a realized loss ceiling or capital survival.

Human owners set the mandate and risk policy. Deterministic quantitative code
computes targets; independent risk governs approval. Analyst and committee
interfaces are advisory. Structured numerical claims are checked against saved
facts, while narrative requires human review. Automatic daily LLM calls are not
connected. The account adapter records intentions with zero confirmed fills.

- [Architecture](ARCHITECTURE.md)
- [Fund operator guide](fund_agents/README.md)
- [Ensemble research](multi_strategy_ensemble/README.md)

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/test_investor_portal.cjs
```
