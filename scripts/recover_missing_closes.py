"""Recover missing daily bars from dated, post-close Yahoo quote snapshots.

Never accept today's price for yesterday. Every quote must carry the requested
session date and a final trade timestamp no earlier than the final minute of
the exchange session. This accommodates a last auction print seconds before
the calendar's nominal close; the snapshot is retrieved after the session.
Save the exact quote fields and adjustment ratio as provenance.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
END = pd.Timestamp('2026-10-20')
CALENDARS = {'.DE': 'XETR', '.PA': 'XPAR', '.AS': 'XAMS', '.BR': 'XBRU',
             '.MC': 'XMAD', '.MI': 'XMIL', '.L': 'XLON', '.SW': 'XSWX',
             '.OL': 'XOSL', '.ST': 'XSTO', '.CO': 'XCSE', '.HE': 'XHEL', '.IR': 'XDUB',
             '.VI': 'XWBO', '.LS': 'XLIS', '.WA': 'XWAR'}


def recover(symbol):
    try:
        calendar = xcals.get_calendar(next(v for k, v in CALENDARS.items() if symbol.endswith(k)))
        close = calendar.session_close(END)
        ticker = yf.Ticker(symbol)
        ticker.history(start='2026-10-19', end='2026-10-21', interval='60m', auto_adjust=False)
        meta = ticker.get_history_metadata()
        at = meta.get('regularMarketTime')
        at = pd.Timestamp(at, unit='s', tz='UTC') if isinstance(at, (int, float)) else pd.Timestamp(at)
        local = at.tz_convert(meta['exchangeTimezoneName'])
        price, previous = float(meta['regularMarketPrice']), float(meta['previousClose'])
        if local.date() != END.date() or at < close - pd.Timedelta(minutes=1) or not np.isfinite([price, previous]).all() or min(price, previous) <= 0:
            raise ValueError('quote is not a valid post-close mark for the requested session')
        return {'ticker': symbol, 'date': str(END.date()), 'regularMarketPrice': price,
                'previousClose': previous, 'regularMarketTime': at.isoformat(),
                'exchange_session_close': close.isoformat(), 'currency': meta.get('currency'),
                'note': 'Final session quote snapshot; timestamp within the final minute or after nominal close. Not an intraday bar proxy.',
                'source': 'Yahoo Finance chart metadata via yfinance',
                'source_url': 'https://finance.yahoo.com/quote/' + symbol + '/'}
    except Exception as exc:
        return {'ticker': symbol, 'error': str(exc)}


def main():
    path = ROOT / 'data/cache/asset_prices.csv'
    prices = pd.read_csv(path, index_col=0, parse_dates=True)
    missing = prices.columns[prices.loc[END].isna()].tolist()
    results = []
    print('Recovering dated closing quotes for', len(missing), 'assets', flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = [pool.submit(recover, c) for c in missing]
        for future in as_completed(jobs):
            item = future.result()
            if 'error' not in item:
                previous = prices.loc[prices.index < END, item['ticker']].dropna().iloc[-1]
                item['cached_previous_close'] = float(previous)
                item['cache_basis_scale'] = float(previous / item['previousClose'])
                item['cache_basis_close'] = item['regularMarketPrice'] * item['cache_basis_scale']
                prices.loc[END, item['ticker']] = item['cache_basis_close']
            results.append(item)
            if len(results) % 50 == 0:
                print('Processed', len(results), flush=True)
    prices.to_csv(path, index_label='Date')
    evidence_path = path.parent / 'recovered_close_quotes.json'
    previous = json.loads(evidence_path.read_text()) if evidence_path.exists() else []
    by_ticker = {v['ticker']: v for v in previous}
    by_ticker.update({v['ticker']: v for v in results})
    evidence_path.write_text(json.dumps(list(by_ticker.values()), indent=2))
    errors = [r for r in results if 'error' in r]
    print('Recovered', len(results) - len(errors), 'unresolved', len(errors), flush=True)
    print(json.dumps(errors, indent=2))


if __name__ == '__main__':
    main()
