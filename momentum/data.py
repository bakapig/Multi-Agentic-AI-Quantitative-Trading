import pandas as pd
from .config import ASSETS, DATA, DATA_START


def download(refresh=False):
    """Adjusted closes (auto_adjust) for ASSETS and the 13-week T-bill yield (^IRX, percent). Cached as CSV in data/momentum/."""
    f, g = DATA / "prices.csv", DATA / "rf_irx.csv"
    if refresh or not (f.exists() and g.exists()):
        import yfinance as yf
        px = yf.download(ASSETS, start=DATA_START, auto_adjust=True, progress=False)["Close"][ASSETS].dropna(how="all")
        px.to_csv(f)
        yf.download("^IRX", start=DATA_START, progress=False, auto_adjust=False)["Close"].squeeze().to_csv(g)
    px = pd.read_csv(f, index_col=0, parse_dates=True)[ASSETS]
    irx = pd.read_csv(g, index_col=0, parse_dates=True).squeeze()
    return px, irx


def weekday_panel(px):
    """raw: prices on a weekday grid (NaN on own-market holidays); ff: forward-filled (holiday return = 0)."""
    raw = px.reindex(pd.bdate_range(px.index.min(), px.index.max()))
    return raw, raw.ffill()


def rf_daily(irx, index):
    return irx.reindex(index).ffill().bfill() / 100 / 252
