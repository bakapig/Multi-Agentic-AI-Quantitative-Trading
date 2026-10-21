"""Reproduce the October 1-20, 2026 standalone research comparison.

Never fill unavailable test-window prices. If the original universe has missing
quotes, publish its last complete window and a separately labeled verified-price
subset for the requested window. No strategy parameters are selected on October.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from momentum.config import ASSETS, DATA, FIN_SPREAD, LAG
from momentum.data import download, weekday_panel, rf_daily
from momentum.strategy import garch_vol_forecasts, run_blend
from multi_strategy_ensemble.backtrader_ensemble import run_backtrader_multi_strategy_suite

START, END = '2026-10-01', '2026-10-20'
CAPITAL = 1_000_000.0
PAIRS = [('CAT', 'DE'), ('UNP', 'CSX'), ('XOM', 'CVX'), ('KO', 'PEP'), ('JNJ', 'ABBV'), ('JPM', 'BAC')]
OUT = ROOT / 'reports/october_2026'


def complete_window(prices, sessions, columns=None):
    """Require observed finite positive test prices on every benchmark session."""
    x = prices.reindex(sessions)
    if columns is not None:
        x = x.loc[:, columns]
    valid = (np.isfinite(x) & (x > 0)).all(axis=0)
    return list(x.columns[valid]), list(x.columns[~valid])


def metrics(ret, name, universe, scope, rf):
    r = ret.dropna()
    if r.empty or not np.isfinite(r).all():
        raise ValueError('Empty or invalid return series: ' + name)
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax().clip(lower=1) - 1
    ex = r - rf.reindex(r.index)
    return {'strategy': name, 'scope': scope, 'start': str(r.index[0].date()),
            'end': str(r.index[-1].date()), 'observations': len(r), 'assets': universe,
            'total_return_pct': float((eq.iloc[-1] - 1) * 100),
            'max_drawdown_pct': float(dd.min() * 100),
            'annualized_volatility_pct': float(r.std() * np.sqrt(252) * 100),
            'annualized_sharpe': float(ex.mean() / ex.std() * np.sqrt(252)) if ex.std() > 0 else None,
            'daily_win_rate_pct': float((r > 0).mean() * 100),
            'illustrative_end_nav': float(CAPITAL * eq.iloc[-1])}


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bt_run(prices, benchmark, columns, end):
    # No bfill, and no missing test bars. Warm-up inputs must also be complete.
    return run_backtrader_multi_strategy_suite(prices.loc[:end, columns], benchmark.loc[:end], PAIRS,
            initial_capital=CAPITAL, start_date=START, end_date=end, warmup_bars=120, min_test_bars=5)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    prices = pd.read_csv(ROOT / 'data/cache/asset_prices.csv', index_col=0, parse_dates=True).loc[:END]
    bm = pd.read_csv(ROOT / 'data/cache/benchmark_SPY.csv', index_col=0, parse_dates=True).iloc[:, 0].loc[:END]
    import exchange_calendars as xcals
    sessions = xcals.get_calendar('XNYS').sessions_in_range(START, END)
    if not sessions.isin(bm.dropna().index).all():
        raise ValueError('SPY does not cover every requested completed XNYS session')
    if prices.index.has_duplicates or bm.index.has_duplicates:
        raise ValueError('Duplicate source dates')
    all_columns = list(prices.columns)
    subset, missing = complete_window(prices, sessions)
    mask = (np.isfinite(prices.reindex(sessions)) & (prices.reindex(sessions) > 0)).all(axis=1)
    incomplete = sessions[~mask.to_numpy()]
    full_end = str((sessions[sessions < incomplete[0]][-1] if len(incomplete) else sessions[-1]).date())
    print('Original universe:', len(all_columns), 'last complete session:', full_end, flush=True)
    print('Verified-price subset:', len(subset), 'excluded:', len(missing), flush=True)
    # Both feeds need a full, positive warm-up. Never allow Backtrader's bfill to
    # manufacture a pre-listing price or silently fill a required test quote.
    for cols, cutoff in ((all_columns, full_end), (subset, END)):
        idx = prices.index.intersection(bm.index)
        idx = idx[idx <= pd.Timestamp(cutoff)]
        idx = idx[idx >= idx[idx < pd.Timestamp(START)][-120]]
        if not np.isfinite(prices.loc[idx, cols]).all().all() or not (prices.loc[idx, cols] > 0).all().all():
            raise ValueError('Invalid source in warm-up/test feed')
    full = bt_run(prices, bm, all_columns, full_end)
    full['equity_curves'].to_csv(OUT / 'original_full_universe_equity.csv', index_label='Date')
    full['regimes'].to_csv(OUT / 'original_full_universe_regimes.csv', index_label='Date')
    print('Original full-universe run complete', flush=True)
    observed = full if not missing else bt_run(prices, bm, subset, END)
    observed['equity_curves'].to_csv(OUT / 'original_verified_subset_equity.csv', index_label='Date')
    observed['regimes'].to_csv(OUT / 'original_verified_subset_regimes.csv', index_label='Date')
    print('Original verified-price subset run complete', flush=True)

    px, irx = download()
    px = px.loc[:END, ASSETS]
    raw, ff = weekday_panel(px)
    gv = garch_vol_forecasts(raw, DATA / 'garch_vol_forecasts.csv')
    rf = rf_daily(irx, ff.index)
    result = run_blend(ff, gv, rf)
    if list(ff.columns) != ASSETS or len(ASSETS) != 20:
        raise ValueError('Unexpected momentum universe')
    # Own-market closures may be carried forward; missing quotes on an open
    # session must be reported rather than mistaken for holiday zero returns.
    market_calendars = {'US': xcals.get_calendar('XNYS'), 'SGX': xcals.get_calendar('XSES')}
    for c in ASSETS:
        own = market_calendars['SGX' if c.endswith('.SI') else 'US'].sessions_in_range(START, END)
        if not px[c].reindex(own).notna().all():
            raise ValueError('Missing momentum quotes on open market sessions: ' + c)
    momentum = result['net'].reindex(sessions)
    if momentum.isna().any():
        raise ValueError('Momentum does not cover the requested window')
    result['W'].loc[START:END].to_csv(OUT / 'momentum_target_weights.csv', index_label='Date')
    result['Wlag'].loc[START:END].to_csv(OUT / 'momentum_held_weights.csv', index_label='Date')
    result['turn'].loc[START:END].to_csv(OUT / 'momentum_turnover.csv', index_label='Date')

    def returns(curves):
        return curves / curves.shift(1).fillna(CAPITAL) - 1
    rf_common = pd.Series((1.04 ** (1 / 252) - 1), index=sessions)
    full_r = returns(full['equity_curves'])
    subset_r = returns(observed['equity_curves'])
    benchmark = bm.pct_change().reindex(sessions)
    table, paths, daily = [], {}, {}

    ensemble_runs = [
        ('full', full_r, len(all_columns), 'Original full universe; ends at last complete price session'),
    ]
    if missing:
        ensemble_runs.append(('verified_subset', subset_r, len(subset), 'Verified-price subset; different universe, not the full original portfolio'))
    for kind, R, n, scope in ensemble_runs:
        for col, label in [('Regime_Routed_Ensemble', 'Original dynamic ensemble'),
                           ('Equal_Weight_1_3', 'Original equal-weight ensemble'),
                           ('Risk_Parity', 'Original inverse-volatility ensemble'),
                           ('Trend_Following', 'Original trend engine'),
                           ('Momentum', 'Original cross-sectional momentum engine'),
                           ('Mean_Reversion', 'Original mean-reversion engine')]:
            key = kind + '__' + col
            daily[key] = R[col]
            paths[key] = (1 + R[col]).cumprod()
            table.append(metrics(R[col], label, n, scope, rf_common))
    windows = [(END, 'Requested October 1-20 window')]
    if full_end != END:
        windows.insert(0, (full_end, 'Aligned with original full-universe window'))
    for end, scope in windows:
        s = momentum.loc[:end]
        table.append(metrics(s, 'New momentum (20 assets)', 20, scope, rf))
        table.append(metrics(benchmark.loc[:end], 'SPY buy-and-hold', 1, scope, rf_common))
    daily['new_momentum_20_assets'] = momentum
    daily['SPY'] = benchmark
    paths['new_momentum_20_assets'] = (1 + momentum).cumprod()
    paths['SPY'] = (1 + benchmark).cumprod()
    daily = pd.DataFrame(daily).reindex(sessions)
    curves = pd.DataFrame(paths).reindex(sessions)
    daily.to_csv(OUT / 'daily_returns.csv', index_label='Date')
    curves.to_csv(OUT / 'normalized_equity.csv', index_label='Date')
    stats = pd.DataFrame(table)
    stats.to_csv(OUT / 'comparison.csv', index=False)
    pd.DataFrame({'excluded_ticker': missing, 'reason': 'Missing observed price on a required test session'}).to_csv(OUT / 'excluded_assets.csv', index=False)
    params = {name: file_hash(ROOT / name) for name in [
        'momentum/config.py', 'momentum/strategy.py', 'multi_strategy_ensemble/config.py',
        'multi_strategy_ensemble/backtrader_ensemble.py', 'multi_strategy_ensemble/regime_detector.py',
        'common/microstructure.py', 'scripts/compare_october_strategies.py']}
    source_names = [
        'data/cache/asset_prices.csv', 'data/cache/benchmark_SPY.csv',
        'data/momentum/prices.csv', 'data/momentum/garch_vol_forecasts.csv', 'data/momentum/rf_irx.csv',
        'data/cache/recovered_close_quotes.json', 'data/momentum/recovered_close.json']
    sources = {name: file_hash(ROOT / name) for name in source_names if (ROOT / name).exists()}
    notes = [
        'Research simulations only; the fund adapter still records intentions with zero confirmed fills.',
        'Original ensemble: existing Backtrader strategies and regime allocations, 120 warm-up bars, starts in cash on October 1. Ensemble NAVs blend standalone sleeve returns; no separate allocator turnover fee is modeled.',
        'Original execution: existing same-close (cheat-on-close) assumption, synthetic high/low at close +/-0.5%, 2 bp slippage, market-specific fees, board lots and short borrow. This is optimistic compared with a tradable next-session simulation.',
        'Backtrader decimal commission units corrected with percabs=True; the previous fee conversion charged 1/100 of the intended rate. Return accounting includes the starting capital and September 30 benchmark close; inverse-vol weights use prior observations.',
        'Original 60-day sleeve risk-parity estimator has fewer than 60 trading observations here; its existing 0.01 fallback gives equal sleeve weights throughout the short test.',
        'New momentum: fixed 50% time-series trend / 50% long-only inverse-volatility core, existing GARCH-t forecasts, 10% target annual volatility, 3x gross cap, lag=2, trading costs and rf+50bp financing above 1x gross. Carries pre-October model positions into the test.',
        'Removing one holding changes the momentum portfolio. No remaining signal, volatility, trading-band or cost parameters were tuned on October results.',
        'Momentum weights are continuous research weights without board-lot rounding. Both research engines mix local-currency asset returns without an FX conversion model; normalized results are not fully reconciled USD account returns.',
        'Own-market holidays are carried forward in momentum; open-market missing quotes are rejected. The ensemble verified subset has observed closes on every SPY session; excluded assets are listed separately.',
        'Annualized Sharpe and volatility use only 13 or 14 observations and are descriptive, not evidence of persistent performance. SPY excludes benchmark transaction costs.',
        'Historical caches and pretrained forecasts are supplied research inputs, not an independently audited point-in-time constituent and corporate-action database.',
        'October 20 recovery: 336 missing daily bars use dated final-session Yahoo quote snapshots, checked against each exchange calendar close and rescaled using the prior close. Their exact prices, timestamps and scaling ratios are saved in data/cache/recovered_close_quotes.json. These are closing marks rather than a complete daily-bar corporate-action audit.',
        'The missing ES3.SI October 20 close of SGD 5.463 is sourced from https://www.eoddata.com/stockquote/SGX/ES3.htm and matches Yahoo previousClose on October 21. This is an observed end-of-day value, not the last intraday bar. Source details are in data/momentum/recovered_close.json.',
    ]
    manifest = {'requested_window': [START, END], 'requested_xnys_sessions': len(sessions),
                'full_original_window': [START, full_end], 'full_original_assets': len(all_columns),
                'full_original_oct20_result_available': not bool(missing),
                'verified_subset_assets': len(subset), 'excluded_asset_count': len(missing),
                'new_momentum_assets': ASSETS, 'initial_research_capital': CAPITAL,
                'source_sha256': sources, 'implementation_sha256': params,
                'upstream_reference': '89b51d6', 'notes': notes, 'orders_enabled': False}
    (OUT / 'run_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    # Seed every curve with the September 30 baseline so first-day P&L and losses
    # from starting capital remain visible. Do not plot missing endpoint values.
    base = pd.DataFrame(1., index=[pd.Timestamp('2026-09-30')], columns=curves.columns)
    plotted = pd.concat([base, curves])
    fig, axes = plt.subplots(2, 1, figsize=(11.8, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    show = [('full__Regime_Routed_Ensemble', f'Original ensemble: {len(all_columns)} assets, through Oct {pd.Timestamp(full_end).day}', '#087f8c', '-'),
            ('new_momentum_20_assets', 'New momentum: 20 assets', '#dc7540', '-'),
            ('SPY', 'SPY reference', '#7b8794', ':')]
    if missing:
        show.insert(1, ('verified_subset__Regime_Routed_Ensemble', f'Original engine: {len(subset)}-asset verified subset', '#6c67c8', '--'))
    for key, label, color, style in show:
        y = plotted[key]
        axes[0].plot(y.index, 100 * (y - 1), label=label, color=color, linestyle=style, linewidth=2, marker='o', markersize=3)
        axes[1].plot(y.index, 100 * (y / y.cummax().clip(lower=1) - 1), color=color, linestyle=style, linewidth=1.7)
    axes[0].set_title('October 1-20, 2026 | Ensemble and new momentum research', loc='left', fontweight='bold', pad=16)
    axes[0].set_ylabel('Cumulative net return (%)')
    axes[1].set_ylabel('Drawdown (%)')
    axes[0].legend(loc='best', fontsize=8.5, frameon=False)
    axes[1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%b %d'))
    for ax in axes:
        ax.axhline(0, color='#b6bec8', linewidth=.7)
        ax.grid(alpha=.18)
        ax.spines[['top', 'right']].set_visible(False)
    coverage_note = f'{len(missing)} missing original quotes; subset is a separate universe.' if missing else 'Full original universe and 20-asset momentum: all 14 test sessions.'
    fig.text(.08, .015, coverage_note + '\nDifferent execution and start-position conventions; research returns, no confirmed fund fills.', fontsize=9, color='#555f6a')
    fig.tight_layout(rect=[0, .06, 1, 1])
    fig.savefig(OUT / 'comparison.png', dpi=170)
    plt.close(fig)

    cols = ['strategy', 'start', 'end', 'assets', 'total_return_pct', 'max_drawdown_pct', 'annualized_sharpe']
    aligned = stats[(stats['scope'].str.startswith('Original full universe') & stats.strategy.eq('Original dynamic ensemble')) |
                    stats.scope.eq('Aligned with original full-universe window')]
    requested = stats[(stats.scope.str.startswith('Verified-price subset') & stats.strategy.eq('Original dynamic ensemble')) |
                      stats.scope.eq('Requested October 1-20 window')]
    if not missing:
        requested = stats[(stats.scope.str.startswith('Original full universe') & stats.strategy.eq('Original dynamic ensemble')) |
                          stats.scope.eq('Requested October 1-20 window')]
        aligned = requested
    def md_table(frame):
        from tabulate import tabulate
        return tabulate(frame[cols], headers='keys', tablefmt='github', showindex=False, floatfmt='.3f')
    report = '# October 2026 strategy comparison\n\n'
    report += f'Requested window: **{START} through {END} inclusive**, {len(sessions)} XNYS sessions.\n\n'
    if missing:
        report += f'**Data limitation:** {len(missing)} of {len(all_columns)} original assets lack a required closing price. '
        report += f'The full original portfolio is only calculable through **{full_end}**. No missing October 20 quote was filled.\n\n'
        report += '## Same-window comparison with the full original universe\n\n' + md_table(aligned) + '\n\n'
        report += '## Requested October 1-20 window\n\nThe original engine below uses a verified-price subset; it is a different portfolio.\n\n' + md_table(requested) + '\n\n'
    else:
        report += f'All **{len(all_columns)} original assets** and **20 momentum assets** have closing marks through October 20. '
        report += 'The missing daily bars were recovered from dated closing quote sources; no test return is manufactured by forward filling a missing close. See source notes below.\n\n'
        report += '## October 1-20 results\n\n' + md_table(requested) + '\n\n'
    report += '![Research comparison](comparison.png)\n\n## Method and limitations\n\n'
    report += '\n'.join('- ' + note for note in notes) + '\n\n'
    report += '## Reproduce from the saved source snapshot\n\n```powershell\n.\\.venv\\Scripts\\python.exe scripts/compare_october_strategies.py\n```\n\n'
    report += 'All engine and ensemble variants are in `comparison.csv`; the saved daily returns, equities, weights, exclusions and SHA-256 manifest make the calculation reviewable.\n'
    (OUT / 'research_report.md').write_text(report, encoding='utf-8')
    def html_table(frame):
        return frame[cols].to_html(index=False, float_format=lambda x: f'{x:,.3f}', border=0)
    page = '<!doctype html><html><head><meta charset="utf-8"><title>October strategy backtests</title><style>'
    page += 'body{font:16px system-ui;background:#f3f6fa;color:#152b3c;margin:0;padding:36px}main{max-width:1180px;margin:auto;background:white;padding:32px;border-radius:16px}h1{margin-top:0}h2{margin-top:32px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:12px 8px;border-bottom:1px solid #dde5ed;text-align:right}th:first-child,td:first-child{text-align:left}img{width:100%}.notice{background:#fff3db;padding:18px;border-radius:8px}li{margin-bottom:10px}a{color:#087f8c}</style></head><body><main>'
    page += '<h1>Ensemble & momentum backtests</h1><p>October 1–20, 2026 · Research simulations · No confirmed fund fills</p>'
    if missing:
        page += f'<p class="notice">{len(missing)} of {len(all_columns)} original assets lack a required closing quote. The full original result ends {full_end}. The subset is a different portfolio.</p>'
        page += '<h2>Aligned comparison: full original universe</h2>' + html_table(aligned)
        page += '<h2>October 1–20: verified-price subset comparison</h2>' + html_table(requested)
    else:
        page += '<p class="notice">14 trading sessions. Complete closing marks for both universes; missing daily bars were recovered from dated closing sources. Different execution and start-position conventions apply.</p>'
        page += '<h2>October 1–20 results</h2>' + html_table(requested)
    page += '<img src="comparison.png" alt="Net cumulative returns and drawdown"><h2>Calculation details</h2><ul>'
    page += ''.join('<li>' + html.escape(n) + '</li>' for n in notes) + '</ul>'
    page += '<p><a href="comparison.csv">All results CSV</a> · <a href="daily_returns.csv">Daily returns</a> · <a href="excluded_assets.csv">Excluded assets</a> · <a href="run_manifest.json">Source and parameter manifest</a></p></main></body></html>'
    (OUT / 'index.html').write_text(page, encoding='utf-8')
    print('\nAligned original-universe comparison:\n', aligned[cols].to_string(index=False))
    print('\nRequested-window subset comparison:\n', requested[cols].to_string(index=False))
    print('Saved', OUT)


if __name__ == '__main__':
    main()
