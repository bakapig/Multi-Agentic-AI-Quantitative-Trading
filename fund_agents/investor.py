"""Ensemble-only public research data. Account amounts never cross this boundary."""
import csv
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import statistics

SERIES = {
    'ensemble': ('Regime_Routed_Ensemble', 'Dynamic ensemble'),
    'equal_weight': ('Equal_Weight_1_3', 'Equal-weight ensemble'),
    'risk_parity': ('Risk_Parity', 'Inverse-volatility ensemble'),
    'trend': ('Trend_Following', 'Trend following'),
    'momentum': ('Momentum', 'Momentum'),
    'mean_reversion': ('Mean_Reversion', 'Mean reversion'),
    'benchmark': ('Benchmark_SPY', 'SPY benchmark'),
}


def number(value):
    if isinstance(value, bool):
        raise ValueError('Expected a finite number')
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Expected a finite number')
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(values, initial):
    returns, previous, peak, drawdowns = [], initial, initial, []
    for value in values:
        returns.append(value / previous - 1)
        previous, peak = value, max(peak, value)
        drawdowns.append(value / peak - 1)
    vol = statistics.stdev(returns) if len(returns) > 1 else 0.
    cash_daily = 1.04 ** (1 / 252) - 1
    return {
        'total_return': values[-1] / initial - 1,
        'max_drawdown': min(drawdowns),
        'annualized_volatility': vol * math.sqrt(252),
        'sharpe': (statistics.mean(returns) - cash_daily) / vol * math.sqrt(252) if vol > 0 else None,
        'positive_days': sum(r > 0 for r in returns), 'observations': len(returns),
    }


def public_replay(replay):
    """Explicit scalar allowlist; no raw account, memo prose, units or prices."""
    if not replay:
        return {'available': False}
    risk, config = replay.get('fund_risk', {}), replay.get('config', {})
    nav = risk.get('metrics', {}).get('marked_nav_usd')
    phantom = risk.get('phantom_book')
    if not isinstance(nav, (int, float)) or not math.isfinite(nav) or nav <= 0 or not phantom:
        return {'available': False}
    def fraction(key):
        return number(phantom[key]) / nav if key in phantom else None
    policies = {}
    for name in ('soft_drawdown', 'maximum_drawdown', 'maximum_fund_gross', 'maximum_name_gross'):
        value = config.get(name)
        if isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1:
            policies[name] = value
    chair_status = replay.get('committee_chair', {}).get('status', 'NOT_RECORDED')
    allowed_status = {'NOT_REQUESTED', 'NOT_RECORDED', 'REJECTED', 'STRUCTURED_CLAIMS_VALIDATED'}
    return {
        'available': True, 'as_of': date.fromisoformat(replay['as_of']).isoformat(),
        'proposed_gross_fraction': fraction('proposed_gross_usd'),
        'approved_gross_fraction': fraction('approved_gross_usd'),
        'removed_gross_fraction': fraction('throttled_gross_usd'),
        'soft_throttle_active': phantom.get('soft_throttle_active') is True,
        'breaker_latched': risk.get('state', {}).get('breaker_latched') is True,
        'record_only': True, 'policies': policies,
        'chair_status': chair_status if chair_status in allowed_status else 'NOT_RECORDED',
    }


def build_investor_data(directory, replay=None):
    directory = Path(directory)
    curve_file = directory / 'original_full_universe_equity.csv'
    regime_file = directory / 'original_full_universe_regimes.csv'
    manifest_file = directory / 'run_manifest.json'
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    start, end = manifest['full_original_window']
    start, end = date.fromisoformat(start).isoformat(), date.fromisoformat(end).isoformat()
    initial = number(manifest['initial_research_capital'])
    if initial <= 0:
        raise ValueError('Invalid research normalization base')
    with curve_file.open(newline='', encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    rows = [r for r in rows if start <= r['Date'] <= end]
    dates = [date.fromisoformat(r['Date']).isoformat() for r in rows]
    if not dates or dates != sorted(set(dates)) or dates[0] != start or dates[-1] != end:
        raise ValueError('Incomplete or unordered research window')
    if len(dates) != manifest['requested_xnys_sessions']:
        raise ValueError('Incomplete research session coverage')
    # This allowlist deliberately never reads mixed-comparison strategy columns.
    series = {}
    for key, (column, label) in SERIES.items():
        values = [number(r[column]) for r in rows]
        if any(v <= 0 for v in values):
            raise ValueError('Nonpositive research curve')
        series[key] = {'label': label, 'metrics': measure(values, initial),
                       'index': [100.] + [100 * v / initial for v in values]}
    with regime_file.open(newline='', encoding='utf-8-sig') as stream:
        regime_rows = [r for r in csv.DictReader(stream) if start <= r['Date'] <= end]
    if [r['Date'] for r in regime_rows] != dates:
        raise ValueError('Regime dates differ from return dates')
    def weights(row):
        result = {key: number(row['weight_' + source]) for key, source in
                  [('trend', 'trend'), ('momentum', 'momentum'), ('mean_reversion', 'reversion'), ('cash', 'cash')]}
        if any(v < 0 or v > 1 for v in result.values()) or not math.isclose(sum(result.values()), 1):
            raise ValueError('Invalid strategy allocation')
        return result
    regimes = [{'date': r['Date'], 'regime': r['regime'], 'weights': weights(r)} for r in regime_rows]
    # No free-form historical narrative or raw account fields enter the API.
    return {
        'schema_version': 'alphahunt-investor-v1',
        'brand': {'name': 'AlphaHunt Capital', 'team': 'alphahunter',
                  'mandate': 'Absolute-return, systematic quantitative research',
                  'objective': 'Seek equity participation with disciplined downside risk.'},
        'backtest': {
            'start': start, 'end': end, 'sessions': len(dates),
            'universe_size': int(manifest['full_original_assets']),
            'universe_scope': 'Global research universe; the connected fund adapter separately uses 14 US equities.',
            'basis': 'Standalone ensemble strategy backtest',
            'dates': [(date.fromisoformat(start) - timedelta(days=1)).isoformat()] + dates,
            'series': series, 'regimes': regimes, 'latest_allocation': regimes[-1],
            'method': [
                'Research simulations; the account adapter records intentions and has no confirmed fills.',
                'Market-specific commissions, board lots, short borrow and modeled 2 bp slippage.',
                'Same-close execution and synthetic high/low bars are optimistic execution assumptions.',
                'Regime allocations use the prior session. The current policy assigns mean reversion zero weight.',
                'Local-currency asset returns have no FX conversion model. These are not reconciled fund returns.',
                'The 14-session sample is too short to establish persistent risk-adjusted performance.',
                'The proposed intraday and 7% halt profile was not applied to this historical backtest.',
            ],
        },
        'risk_replay': public_replay(replay),
        'proposed_profile': {'intraday_halt': .025, 'maximum_drawdown': .07,
                             'status': 'PROPOSED', 'human_review_to_resume': True,
                             'intraday_monitor_connected': False},
        'governance': {'automatic_model_calls': False, 'numerical_claim_checks': True,
                       'free_text_requires_human_review': True, 'risk_override_by_ai': False},
        'provenance': {'source_commit': manifest.get('upstream_reference'),
                       'curve_sha256': digest(curve_file), 'regime_sha256': digest(regime_file),
                       'manifest_sha256': digest(manifest_file),
                       'normalization': '100 at the start; percentage performance only',
                       'final_quote_recovery': '336 missing final daily bars were recovered from dated session-closing quote snapshots.'},
    }
