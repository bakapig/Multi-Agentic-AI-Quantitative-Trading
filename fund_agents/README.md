# Ensemble fund integration

Updated 20 October 2026. `fund_agents` connects the teammate's three numerical
engines through one Ensemble PM. The old standalone Pairs PM, its vendored
Kalman/OU/forecast/formation modules and pair-specific account fields are removed.
The ensemble's separate mean-reversion engine remains available.

For the FE5209 presentation, use the
[technical investor pitch and Q&A](../presentations/architecture_20261020/FE5209_Technical_Investor_Pitch_Script.txt).

For a developer explanation and spoken screen tour, use the
[build and demo script](../presentations/architecture_20261020/Ensemble_System_Build_and_Demo_Script.txt).
The [PowerShell launcher](../scripts/start_ensemble_web_app.ps1) generates a cycle
and starts the web app; use `-Mode research` for the cached historical replay.

## Run a synthetic demonstration

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-fund.txt
.\.venv\Scripts\python.exe -m fund_agents
.\.venv\Scripts\python.exe -m fund_agents.dashboard
```

The demo uses 240 invented XNYS sessions ending 16 October 2026. Open
<http://127.0.0.1:8765> and choose Synthetic demos. All strategy targets, risk
approvals and review tools refer to one saved cycle. No real order or fill occurs.

## Run a historical research cycle

```powershell
.\.venv\Scripts\python.exe -m fund_agents --config config/fund_agents.research.json --as-of 2026-10-16 --prices data/cache/asset_prices.csv --benchmark-prices data/cache/benchmark_SPY.csv --sectors data/cache/full_universe_sectors.csv
```

The adapter uses the configured 14 USD US equities and SPY. Supply a Date-indexed
CSV of equity closes. Include SPY directly or provide a separate benchmark CSV
with a `Close` or `SPY` column. The optional sector CSV has unique `Ticker` and
`Sector` columns and enables sector-neutral momentum. Omitting it uses the
research engine's global top-k momentum mode.

The valuation date must match the supplied account and cannot precede a saved
account cycle. The latest required session must have closed. Future rows are
excluded, closed-calendar rows are counted and excluded, and every remaining
required session and price must be present. No forward or backward filling occurs.
Missing or stale input produces an INPUT_HOLD report and no intentions.

## Allocation and risk

Set `allocation_method` in the JSON config to:

- `regime`: use the existing regime detector's strategy and cash weights.
- `equal_weight`: allocate one third to each engine.
- `risk_parity`: normalize inverse strategy volatility over 60 observed sessions.

The regime policy currently assigns mean reversion 0% in every market state.
The dashboard shows this as standby. This preserves the teammate's current
numerical policy. Mean reversion is used under the other allocation methods.

The engines expose closing-session target weights without converting their
simulated positions into actual account holdings. The adapter aggregates shared
symbols into one Ensemble PM portfolio. Risk reviews NAV, collateral, fee reserve,
gross exposure, symbol concentration, soft drawdown throttling and a persistent
hard drawdown breaker. It applies common scaling to the portfolio targets.
The Phantom Book reports proposed and approved exposure, without claiming profits.

The USD 5M default mandate combines the previous two strategy budgets into USD
3M for the ensemble, with USD 2M central cash. It is configurable. The connected
adapter supports explicit USD US equities with XNYS sessions; wider multi-market
integration requires FX and calendar support. The standalone research runners
remain available separately and their results do not represent this fund.

## Confirmed account snapshot

Without `--portfolio`, the input account is explicitly flat with the configured
cash. To supply actual confirmed holdings, use `--portfolio snapshot.json`:

```json
{
  "as_of": "2026-10-16",
  "ensemble_cash_usd": 3000000,
  "central_cash_usd": 2000000,
  "peak_nav_usd": 5000000,
  "holdings": []
}
```

Each holding uses `pm: "ensemble"`, `group: "portfolio"`, `symbol`, signed `units`
and `entry_price_usd`. An optional `opened_on` is a session date. Reconcile cash
with actual purchases, short proceeds and liabilities. The account fields are
confirmed inputs; an intention receipt never changes them.

Legacy pair-account fields and PM identities are rejected. New defaults use
`ensemble-fund-{demo,research}`, separate `runtime/ensemble_fund.*.sqlite` stores
and `runs/fund_agents/ensemble/{demo,research}` exports. State and reports use
`ensemble-fund-v3`. Old saved accounts and reports are not migrated or indexed.

## Advisory evidence and execution records

The Ensemble PM representative exposes `inspect_signals`, `inspect_model_health`
and `inspect_positions`. The Committee Chair reviews exposure, the Phantom Book
and PM evidence after risk. Default calls and summaries are deterministic.
Automatic LLM calls are pending.

Optional `--pm-responses replies.json` envelopes use keys `ensemble` and/or
`chair`, each with `tool_names` and `reply`. Imported replies must match the exact
facts digest and copied metric claims. A rejected reply does not change any
quantitative decision. Free-text narrative requires human review.

Execution checks the exact persisted risk approval and snapshot, then records
an idempotent `PORTFOLIO_BASKET_RECORD_ONLY` intention. Every receipt has zero
fills. SQLite saves the complete cycle atomically; JSON and closing-price exports
feed the GET-only investor portal. Quote/lot validation, borrow checks, fills,
costed accounting and consolidated fund performance are future work.

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_fund_agents.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_fund_dashboard.py
node --test tests/test_investor_portal.cjs
```

See [the current architecture](../ARCHITECTURE.md) and
[slide diagram](../presentations/architecture_20261020/ensemble_architecture.html).
