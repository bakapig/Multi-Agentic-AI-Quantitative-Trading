"""AlphaHunt Capital: ensemble-only research backtest, October 1-20 by default."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from multi_strategy_ensemble.backtrader_ensemble import run_backtrader_multi_strategy_suite
from fund_agents.investor import SERIES, build_investor_data

PAIRS = [('CAT', 'DE'), ('UNP', 'CSX'), ('XOM', 'CVX'), ('KO', 'PEP'), ('JNJ', 'ABBV'), ('JPM', 'BAC')]


def complete_window(prices, sessions, columns=None):
    panel = prices.reindex(sessions)
    if columns is not None:
        panel = panel.loc[:, columns]
    valid = (np.isfinite(panel) & (panel > 0)).all(axis=0)
    return list(panel.columns[valid]), list(panel.columns[~valid])


def metrics(ret, name, universe, scope, rf):
    r = ret.dropna()
    if r.empty or not np.isfinite(r).all():
        raise ValueError('Invalid return series')
    eq = (1 + r).cumprod()
    ex = r - rf.reindex(r.index)
    return {'strategy': name, 'scope': scope, 'start': str(r.index[0].date()),
            'end': str(r.index[-1].date()), 'observations': len(r), 'assets': universe,
            'total_return_pct': float((eq.iloc[-1] - 1) * 100),
            'max_drawdown_pct': float((eq / eq.cummax().clip(lower=1) - 1).min() * 100),
            'annualized_volatility_pct': float(r.std() * np.sqrt(252) * 100),
            'annualized_sharpe': float(ex.mean() / ex.std() * np.sqrt(252)) if ex.std() > 0 else None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--start', default='2026-10-01')
    ap.add_argument('--end', default='2026-10-20')
    ap.add_argument('--output', type=Path, default=ROOT / 'reports/october_2026')
    args = ap.parse_args(argv)
    import exchange_calendars as xcals
    sessions = xcals.get_calendar('XNYS').sessions_in_range(args.start, args.end)
    prices_path, bench_path = ROOT / 'data/cache/asset_prices.csv', ROOT / 'data/cache/benchmark_SPY.csv'
    prices = pd.read_csv(prices_path, index_col=0, parse_dates=True).loc[:args.end]
    benchmark = pd.read_csv(bench_path, index_col=0, parse_dates=True).iloc[:, 0].loc[:args.end]
    if any(c.endswith('-USD') or c.endswith('USDT') for c in prices.columns):
        raise ValueError('The ensemble cache must contain only the declared equity research universe')
    _, missing = complete_window(prices, sessions)
    if missing or not benchmark.reindex(sessions).notna().all():
        raise ValueError('Incomplete observed test quotes; refresh sources before publishing')
    capital = 1_000_000.  # Simulation normalization only; never an actual fund balance.
    result = run_backtrader_multi_strategy_suite(prices, benchmark, PAIRS,
        initial_capital=capital, start_date=args.start, end_date=args.end, warmup_bars=120, min_test_bars=5)
    args.output.mkdir(parents=True, exist_ok=True)
    equity = result['equity_curves']
    if not equity.index.equals(sessions):
        raise ValueError('Return dates do not match all requested completed sessions')
    equity.to_csv(args.output / 'original_full_universe_equity.csv', index_label='Date')
    result['regimes'].to_csv(args.output / 'original_full_universe_regimes.csv', index_label='Date')
    returns = equity / equity.shift(1).fillna(capital) - 1
    returns.to_csv(args.output / 'daily_returns.csv', index_label='Date')
    manifest = {
        'brand': 'AlphaHunt Capital', 'scope': 'Standalone ensemble strategy research',
        'requested_window': [args.start, args.end], 'full_original_window': [args.start, args.end],
        'requested_xnys_sessions': len(sessions), 'full_original_assets': result['universe_size'],
        'full_original_oct20_result_available': True, 'excluded_asset_count': 0,
        'initial_research_capital': capital,
        'upstream_reference': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in (prices_path, bench_path)},
        'implementation_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            'multi_strategy_ensemble/backtrader_ensemble.py', 'multi_strategy_ensemble/regime_detector.py',
            'common/microstructure.py', 'scripts/run_ensemble_backtest.py')},
        'risk_profile_applied': 'Existing standalone research allocation; proposed intraday/7% profile not applied',
        'orders_enabled': False,
    }
    (args.output / 'run_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    rf = pd.Series(1.04 ** (1 / 252) - 1, index=sessions)
    rows = [metrics(returns[column], label, 1 if key == 'benchmark' else result['universe_size'],
                    'Ensemble-only research', rf) for key, (column, label) in SERIES.items()]
    pd.DataFrame(rows).to_csv(args.output / 'comparison.csv', index=False)
    public = build_investor_data(args.output)
    normalized = pd.DataFrame({s['label']: s['index'] for s in public['backtest']['series'].values()},
                               index=public['backtest']['dates'])
    normalized.to_csv(args.output / 'normalized_equity.csv', index_label='Date')
    (args.output / 'investor_research.json').write_text(json.dumps(public, indent=2), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    dates = pd.to_datetime(normalized.index)
    for label, color, style in [('Dynamic ensemble', '#087f79', '-'), ('SPY benchmark', '#a18a53', '--')]:
        curve = normalized[label]
        axes[0].plot(dates, curve - 100, color=color, linestyle=style, linewidth=2.4, label=label)
        axes[1].plot(dates, 100 * (curve / curve.cummax().clip(lower=100) - 1), color=color, linestyle=style)
    axes[0].set_title(f'AlphaHunt Capital | Ensemble backtest | {args.start} to {args.end}', loc='left', fontweight='bold')
    axes[0].set_ylabel('Cumulative return (%)'); axes[1].set_ylabel('Drawdown (%)')
    axes[0].legend(frameon=False)
    for ax in axes:
        ax.grid(alpha=.18); ax.spines[['top', 'right']].set_visible(False)
    fig.text(.09, .025, 'Standalone strategy research · Modeled costs · No confirmed fund returns\nProposed 2.5% intraday / 7% halt profile was not applied.', fontsize=9, color='#617480')
    fig.tight_layout(rect=[0, .06, 1, 1]); fig.savefig(args.output / 'comparison.png', dpi=160); plt.close(fig)
    table = pd.DataFrame(rows)[['strategy', 'total_return_pct', 'max_drawdown_pct', 'annualized_sharpe']]
    report = '# AlphaHunt Capital — ensemble research\n\n'
    report += f'{args.start} through {args.end}, {len(sessions)} trading sessions. Percentage returns; normalized index starts at 100.\n\n'
    report += table.to_markdown(index=False, floatfmt='.3f') + '\n\n![Ensemble backtest](comparison.png)\n\n'
    report += 'The research universe contains ' + str(result['universe_size']) + ' global assets. The connected account adapter separately uses 14 US equities. These results are standalone research, not actual fund NAV performance.\n\n'
    report += '\n'.join('- ' + line for line in public['backtest']['method'])
    report += '\n\nReproduce with `python scripts/run_ensemble_backtest.py --start 2026-10-01 --end 2026-10-20`.\n'
    (args.output / 'research_report.md').write_text(report, encoding='utf-8')
    (args.output / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>AlphaHunt Capital</title><meta http-equiv="refresh" content="0;url=http://127.0.0.1:8765/#performance"><p><a href="http://127.0.0.1:8765/#performance">Open AlphaHunt Capital ensemble backtesting</a></p>', encoding='utf-8')
    print(table.to_string(index=False))
    print('Saved ensemble-only research:', args.output)


if __name__ == '__main__':
    main()
