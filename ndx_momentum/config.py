"""Frozen parameters of the NDX momentum-hedge strategy (replication of ndx-momentum-hedge-main). Do not retune on data after 2026-10-01."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA, RES, LIVE = ROOT / "data" / "ndx_momentum", ROOT / "reports" / "ndx_momentum", ROOT / "live" / "ndx_momentum"

# rule: every HOLD trading days, keep LOOKBACK-day momentum > 0, rank by MOM_5D-day momentum, top TOP_K equal weight, 50% stocks + 50% PSQ
TOP_K, LOOKBACK, MOM_5D, HOLD = 5, 20, 5, 5
STOCK_FRAC, HEDGE_FRAC = 0.5, 0.5
START_DATE = "2021-06-07"               # anchors the weekly grid (repo START_DATE)
REPO_END = "2026-08-06"                 # end of the repo's published backtest
ANCHOR_DATE = "2026-10-15"              # date of data/ndx_momentum/ndx_constituents_anchor.csv
SEEN_END, TEST_START = "2026-09-30", "2026-10-01"
DRIFT_TOL = 1e-5

CLASS_MATE = {a: b for g in [("GOOGL", "GOOG"), ("FOXA", "FOX"), ("LBTYA", "LBTYK")] for a, b in (g, g[::-1])}
YAHOO_ALIAS = {"FISV": "FI"}            # Yahoo serves Fiserv as FISV; the membership data uses FI
BENCH, HEDGE = "QQQ", "PSQ"

# Variants reported daily. The first is primary: point-in-time members, fill at the next close, 10 bp on stock turnover.
# The second is repo-faithful: hard-coded list (hindsight bias), fill at the signal close, no costs.
VARIANTS = {
    "pit_next_close_10bp": dict(universe="pit", lag=1, cost_bps=10.0),
    "static_repo_signal_close_0bp": dict(universe="static", lag=0, cost_bps=0.0),
}
PRIMARY = "pit_next_close_10bp"

NDX_100 = [
    'NVDA', 'AAPL', 'AVGO', 'META', 'MU', 'MSFT', 'AMD', 'AMZN', 'TSLA', 'GOOGL',
    'GOOG', 'INTC', 'ASML', 'CSCO', 'COST', 'AMAT', 'LRCX', 'NFLX', 'PLTR', 'PANW',
    'ARM', 'TXN', 'KLAC', 'LIN', 'AMGN', 'CRWD', 'PEP', 'ADBE', 'ADI',
    'QCOM', 'BKNG', 'WDAY', 'MRVL', 'INTU', 'CDNS', 'SNPS', 'PCAR', 'NXPI', 'FTNT',
    'MCHP', 'ROP', 'ODFL', 'MAR', 'CPRT', 'ORLY', 'CTAS', 'PAYX', 'AZN', 'MNST',
    'KDP', 'DASH', 'DDOG', 'MDB', 'TTD', 'TEAM', 'KHC', 'XEL', 'EXC',
    'GEHC', 'CSGP', 'BKR', 'ROST', 'LULU', 'IDXX', 'FAST', 'EA', 'VRTX', 'REGN',
    'GFS', 'SBUX', 'CMCSA', 'ADP', 'MELI', 'GILD', 'MDLZ', 'ZS', 'WBD', 'PDD', 'MRNA', 'DXCM',
    'CRM', 'NOW', 'ISRG', 'BIIB', 'CEG', 'CDW', 'CHTR', 'DLTR', 'FANG', 'ILMN',
    'MSTR', 'ON', 'PYPL', 'RIVN', 'SMCI', 'TTWO', 'VRSK', 'ZM',
]
