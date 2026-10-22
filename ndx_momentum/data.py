import pandas as pd
from datetime import date
from .config import BENCH, DATA, HEDGE, NDX_100, YAHOO_ALIAS
from .universe import PIT

PRICES = DATA / "prices.csv.gz"
YAHOO_FROM = "2019-01-01"


def needed_tickers():
    """Static list + every point-in-time member since 2021-04 + QQQ + PSQ (membership naming)."""
    return sorted(set(NDX_100) | PIT().all_tickers_since("2021-04-01", date.today().isoformat()) | {BENCH, HEDGE})


def yahoo_symbol(t):
    return {v: k for k, v in YAHOO_ALIAS.items()}.get(t, t)


def fetch(tickers=None):
    """Adjusted closes from Yahoo (auto_adjust), columns in membership naming. Network access."""
    import yfinance as yf
    tickers = tickers or needed_tickers()
    sym, parts = [yahoo_symbol(t) for t in tickers], []
    for i in range(0, len(sym), 40):
        p = yf.download(sym[i:i + 40], start=YAHOO_FROM, auto_adjust=True, progress=False)["Close"]
        parts.append(p if isinstance(p, pd.DataFrame) else p.to_frame(sym[i]))
    df = pd.concat(parts, axis=1).dropna(how="all").rename(columns=YAHOO_ALIAS)
    df.index = pd.DatetimeIndex(df.index).tz_localize(None)
    return df


def load_panel():
    """Cached snapshot (data/ndx_momentum/prices.csv.gz) as a DataFrame, membership naming, date index."""
    df = pd.read_csv(PRICES, index_col=0, parse_dates=True).rename(columns=YAHOO_ALIAS)
    return df.dropna(axis=1, how="all")


def to_dict(df, min_obs=20):
    """{ticker: {YYYY-MM-DD: adjusted close}}; tickers with fewer than min_obs bars are treated as unavailable."""
    out = {}
    for t in df.columns:
        s = {d.strftime("%Y-%m-%d"): float(v) for d, v in df[t].dropna().items() if v > 0}
        if len(s) >= min_obs:
            out[t] = s
    return out


def load_prices():
    prices = to_dict(load_panel())
    if BENCH not in prices or HEDGE not in prices:
        raise RuntimeError("QQQ/PSQ missing from the price snapshot")
    return prices
