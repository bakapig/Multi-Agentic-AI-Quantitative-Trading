"""Protect reporting boundaries and execution-cost units for October research."""
import unittest
import numpy as np
import pandas as pd

from common.microstructure import create_market_commission
from multi_strategy_ensemble.backtrader_ensemble import compute_bt_metrics
from scripts.compare_october_strategies import complete_window, metrics


class ComparisonTests(unittest.TestCase):
    def test_commissions_charge_the_declared_basis_points(self):
        for ticker, bps in [('CAT', 3.5), ('D05.SI', 12), ('ADS.DE', 8)]:
            with self.subTest(ticker=ticker):
                scheme = create_market_commission(ticker)
                self.assertAlmostEqual(scheme.getcommission(100, 100), 10_000 * bps / 10_000)

    def test_missing_endpoint_quote_excludes_an_asset_without_fill(self):
        dates = pd.to_datetime(['2026-10-19', '2026-10-20'])
        prices = pd.DataFrame({'A': [100, 101], 'B': [50, np.nan], 'C': [10, 0]}, index=dates)
        before = prices.copy()
        kept, excluded = complete_window(prices, dates)
        self.assertEqual(kept, ['A'])
        self.assertEqual(excluded, ['B', 'C'])
        pd.testing.assert_frame_equal(prices, before)

    def test_first_day_loss_counts_in_both_return_and_drawdown(self):
        dates = pd.bdate_range('2026-10-01', periods=5)
        r = pd.Series([-.1, 0., 0., 0., 0.], index=dates)
        result = metrics(r, 'Test', 1, 'Test', pd.Series(0., index=dates))
        self.assertAlmostEqual(result['total_return_pct'], -10)
        self.assertAlmostEqual(result['max_drawdown_pct'], -10)
        self.assertEqual(result['observations'], 5)
        bt = compute_bt_metrics(pd.Series(900., index=dates), 1000.)
        self.assertAlmostEqual(bt['Total Return (%)'], -10)
        self.assertAlmostEqual(bt['Max Drawdown (%)'], -10)


if __name__ == '__main__':
    unittest.main()
