"""Extend the frozen ensemble cache using observed, adjusted Yahoo closes.

Only append dates after the cache boundary; rescale each downloaded series onto
its cached adjustment basis at the last overlapping observation. Missing quotes
remain missing. This does not synthesize October 20 prices from October 19.
"""
import argparse
import json
from pathlib import Path
import sys

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def refresh(end):
    path = ROOT / 'data/cache/asset_prices.csv'
    old = pd.read_csv(path, index_col=0, parse_dates=True)
    boundary = old.index.max()
    end = pd.Timestamp(end)
    if boundary >= end:
        print('Cache already reaches', end.date())
        return
    start = str((boundary - pd.Timedelta(days=10)).date())
    frames = []
    tickers = list(old.columns)
    for i in range(0, len(tickers), 75):
        group = tickers[i:i + 75]
        px = yf.download(group, start=start, end=str((end + pd.Timedelta(days=1)).date()),
                         auto_adjust=True, progress=False, threads=8)['Close']
        if isinstance(px, pd.Series):
            px = px.to_frame(group[0])
        px.index = pd.DatetimeIndex(px.index).tz_localize(None)
        frames.append(px)
        print('Fetched', min(i + 75, len(tickers)), '/', len(tickers), flush=True)
    fresh = pd.concat(frames, axis=1).reindex(columns=tickers)
    scales = {}
    for c in tickers:
        common = old[c].dropna().index.intersection(fresh[c].dropna().index)
        common = common[common <= boundary]
        if len(common):
            at = common[-1]
            scales[c] = float(fresh.at[at, c] / old.at[at, c])
    post = fresh.loc[(fresh.index > boundary) & (fresh.index <= end)]
    post = post.div(pd.Series(scales).reindex(tickers), axis=1)
    if end not in post.index or post.loc[end].notna().sum() == 0:
        raise RuntimeError('No observed closes on requested endpoint; cache was not changed')
    out = pd.concat([old, post])
    out.to_csv(path, index_label='Date')
    spy = ROOT / 'data/cache/benchmark_SPY.csv'
    bm = pd.read_csv(spy, index_col=0, parse_dates=True)
    raw_spy = fresh['SPY'].dropna()
    overlap = bm.index.intersection(raw_spy.index)
    at = overlap[overlap <= bm.index.max()][-1]
    scale = raw_spy.loc[at] / bm.iloc[:, 0].loc[at]
    new_spy = (raw_spy.loc[raw_spy.index > bm.index.max()] / scale).to_frame(bm.columns[0])
    pd.concat([bm, new_spy]).to_csv(spy, index_label='Date')
    manifest = {'source': 'Yahoo Finance via yfinance; auto_adjust=True',
                'pinned_through': str(boundary.date()), 'requested_end': str(end.date()),
                'observed_endpoint_assets': int(post.loc[end].notna().sum()),
                'missing_endpoint_assets': post.columns[post.loc[end].isna()].tolist(),
                'adjustment_scales': scales, 'missing_prices_filled': False}
    (path.parent / 'refresh_manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: v for k, v in manifest.items() if k != 'adjustment_scales'}, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--end', default='2026-10-20')
    refresh(ap.parse_args().end)
