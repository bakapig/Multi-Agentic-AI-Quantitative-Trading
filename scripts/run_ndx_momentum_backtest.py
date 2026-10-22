#!/usr/bin/env python3
"""Weekly backtests of the NDX momentum-hedge rule on the cached snapshot -> reports/ndx_momentum/ (no network)."""

import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402
from ndx_momentum import config as C  # noqa: E402
from ndx_momentum.data import load_prices  # noqa: E402
from ndx_momentum.strategy import backtest, calendar, stats  # noqa: E402

SETTINGS = {
    "static_repo_signal_close_0bp": dict(universe="static", lag=0, cost_bps=0.0),
    "static_next_close_10bp": dict(universe="static", lag=1, cost_bps=10.0),
    "pit_signal_close_0bp": dict(universe="pit", lag=0, cost_bps=0.0),
    "pit_signal_close_10bp": dict(universe="pit", lag=0, cost_bps=10.0),
    "pit_next_close_10bp": dict(universe="pit", lag=1, cost_bps=10.0),
}


def main():
    C.RES.mkdir(parents=True, exist_ok=True)
    prices = load_prices()
    last = calendar(prices)[-1]
    rows = []
    for end_name, end in [("repo_window_to_2026-08-06", C.REPO_END), (f"to_last_bar_{last}", last)]:
        for name, kw in SETTINGS.items():
            r = backtest(prices, end=end, **kw)
            if kw["lag"] == 0:
                q = stats(r["qqq_values"], r["dates"])          # QQQ buy-and-hold on the repo's signal-close grid
            rows.append(dict(window=end_name, setting=name, **{k: round(float(v), 2) for k, v in stats(r["values"], r["dates"]).items()}))
            if end == C.REPO_END:
                pd.DataFrame(r["log"]).to_csv(C.RES / f"trade_log_{name}.csv", index=False)
        rows.append(dict(window=end_name, setting="QQQ_buy_and_hold", **{k: round(float(v), 2) for k, v in q.items()}))
    out = pd.DataFrame(rows)
    out.to_csv(C.RES / "performance.csv", index=False)
    print(out.to_string(index=False))
    (C.RES / "PARAMETER_MANIFEST.json").write_text(json.dumps(dict(
        rule="20d momentum > 0 filter, rank by 5d momentum, top 5 equal weight (50%) + 50% PSQ, every 5 trading days",
        top_k=C.TOP_K, lookback=C.LOOKBACK, rank_window=C.MOM_5D, hold=C.HOLD, start_date=C.START_DATE, membership_anchor=C.ANCHOR_DATE,
        variants=C.VARIANTS, primary=C.PRIMARY, last_bar=last, source="ndx-momentum-hedge-main (backtest_5y.py v2.0, backtest_pit.py)",
        config_sha256=hashlib.sha256((C.ROOT / "ndx_momentum" / "config.py").read_bytes()).hexdigest()), indent=2))


if __name__ == "__main__":
    main()
