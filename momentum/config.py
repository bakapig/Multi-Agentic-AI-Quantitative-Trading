"""Frozen parameters of the momentum strategy: 50% trend sleeve + 50% risk-parity core, GARCH(1,1)-t volatility targeting.
Do not retune on data after 2026-10-01 (graded test window)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA, RES, LIVE = ROOT / "data" / "momentum", ROOT / "reports" / "momentum", ROOT / "live" / "momentum"

CORE_ASSETS = ["SPY", "QQQ", "TLT", "GLD", "USO", "BTC-USD", "ES3.SI", "D05.SI", "O39.SI", "U11.SI"]
BREADTH_ASSETS = ["EFA", "EEM", "EWJ", "IEF", "LQD", "HYG", "DBC", "DBA", "CPER", "UUP", "FXY"]
ASSETS = CORE_ASSETS + BREADTH_ASSETS
DATA_START = "2004-01-01"
EVAL_START = "2006-01-02"

COST_BPS = {"default": 10, ".SI": 25, "BTC-USD": 20}
FIN_SPREAD = 0.005                      # financing spread over rf on gross exposure above 1x NAV

LOOKBACKS = [63, 126, 252]              # trend signal: mean of sign(log return over L days)
GARCH_WINDOW, GARCH_MIN_OBS, REFIT_EVERY = 1500, 500, 63
CORR_WINDOW = 120
TARGET_VOL, MAX_LEVERAGE = 0.10, 3.0
TREND_EVERY, TREND_BAND, TREND_ETA = 5, 0.5, 0.5      # weekly rebalance, no-trade band, partial adjustment
CORE_EVERY, CORE_BAND = 21, 0.25                      # monthly
W_TREND, W_CORE = 0.5, 0.5
LAG = 2                                 # signal at close t, fill at close t+1 (also removes SGX-before-US look-ahead)
TRADING_DAYS = 252

VALIDATION_END, SEEN_END, TEST_START = "2023-09-30", "2026-09-30", "2026-10-01"
