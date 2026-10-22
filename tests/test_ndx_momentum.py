import unittest
from datetime import datetime, timezone
from unittest import mock

import numpy as np
import pandas as pd

from ndx_momentum import strategy
from ndx_momentum.config import ANCHOR_DATE, DATA, HOLD, LOOKBACK, REPO_END
from ndx_momentum.live import drop_incomplete, history_drift, splice, trim_tail
from ndx_momentum.universe import PIT

HAS_SNAPSHOT = (DATA / "prices.csv.gz").exists()


def toy_prices(n=80, tickers=("A", "B", "C", "D", "E", "F", "G", "H"), seed=0):
    """Deterministic business-day prices with distinct trends, plus QQQ and PSQ."""
    rng, dates = np.random.default_rng(seed), pd.bdate_range("2024-01-02", periods=n)
    out = {}
    for i, t in enumerate(tickers):
        px = 100 * np.exp(np.cumsum(rng.normal(0.002 * (i - 3), 0.01, n)))
        out[t] = {d.strftime("%Y-%m-%d"): float(v) for d, v in zip(dates, px)}
    out["QQQ"] = {d.strftime("%Y-%m-%d"): float(100 * (1 + 0.001 * k)) for k, d in enumerate(dates)}
    out["PSQ"] = {d.strftime("%Y-%m-%d"): float(100 * (1 - 0.001 * k)) for k, d in enumerate(dates)}
    return out, [d.strftime("%Y-%m-%d") for d in dates]


class NdxMomentumTests(unittest.TestCase):
    def test_pit_membership_follows_the_change_log(self):
        pit = PIT()
        self.assertIn("WBD", pit.members("2026-10-08"))
        self.assertNotIn("MRNA", pit.members("2026-10-08"))
        self.assertIn("MRNA", pit.members("2026-10-09"))
        self.assertNotIn("WBD", pit.members("2026-10-09"))
        self.assertEqual(pit.members(ANCHOR_DATE), pit.members("2026-10-20"))
        self.assertIn("CSGP", pit.members("2026-05-15"))
        self.assertNotIn("CSGP", pit.members("2026-05-18"))

    def test_select_filters_on_20d_momentum_and_ranks_by_5d(self):
        prices, dates = toy_prices()
        idx = 60
        picks = strategy.select(prices, dates, idx, [t for t in prices if t not in ("QQQ", "PSQ")])
        cur, d20, d5 = dates[idx], dates[idx - LOOKBACK], dates[idx - 5]
        want = sorted(((t, prices[t][cur] / prices[t][d5] - 1) for t in prices if t not in ("QQQ", "PSQ") and prices[t][cur] / prices[t][d20] > 1),
                      key=lambda x: -x[1])[:5]
        self.assertEqual([p[0] for p in picks], [w[0] for w in want])
        self.assertTrue(all(p[2] > 0 for p in picks))
        self.assertLessEqual(len(picks), 5)

    def test_picks_do_not_depend_on_future_prices(self):
        prices, dates = toy_prices()
        members = [t for t in prices if t not in ("QQQ", "PSQ")]
        base = strategy.select(prices, dates, 60, members)
        shocked = {t: {d: (v * 5 if d > dates[60] and t not in ("QQQ", "PSQ") else v) for d, v in px.items()} for t, px in prices.items()}
        self.assertEqual(base, strategy.select(shocked, dates, 60, members))

    def test_one_share_class_per_company_in_pit_mode(self):
        prices, dates = toy_prices(tickers=("GOOGL", "GOOG", "A", "B", "C", "D", "E"))
        for t in ("GOOGL", "GOOG"):                                   # make both classes the strongest names
            prices[t] = {d: v * (1 + 0.004 * k) for k, (d, v) in enumerate(prices[t].items())}
        picks = [p[0] for p in strategy.select(prices, dates, 70, [t for t in prices if t not in ("QQQ", "PSQ")], dedupe=True)]
        self.assertFalse({"GOOGL", "GOOG"} <= set(picks))

    def test_stock_that_stops_trading_is_sold_at_its_last_price(self):
        px = {"2024-01-02": 100.0, "2024-01-03": 110.0, "2024-01-04": 120.0}
        dates = list(px) + ["2024-01-05", "2024-01-08"]
        self.assertAlmostEqual(strategy.pick_return(px, dates, 0, 4), 0.20)

    def test_stats_total_return_and_drawdown(self):
        s = strategy.stats([100.0, 110.0, 99.0, 108.9], ["2024-01-05", "2024-01-12", "2024-01-19", "2024-01-26"])
        self.assertAlmostEqual(s["total_return_pct"], 8.9)
        self.assertAlmostEqual(s["max_drawdown_pct"], -10.0)

    def test_backtest_splits_capital_between_stocks_and_psq_and_costs_reduce_return(self):
        prices, dates = toy_prices(n=90)
        with mock.patch("ndx_momentum.universe.NDX_100", [t for t in prices if t not in ("QQQ", "PSQ")]):
            a = strategy.backtest(prices, "static", start=dates[0], end=dates[-1], cost_bps=0.0)
            b = strategy.backtest(prices, "static", start=dates[0], end=dates[-1], cost_bps=50.0)
        self.assertLess(b["values"][-1], a["values"][-1])
        for r in a["log"]:
            self.assertAlmostEqual(r["strat_ret_pct"], 0.5 * r["stock_ret_pct"] + 0.5 * r["psq_ret_pct"], delta=0.011)

    def test_drop_incomplete_keeps_only_bars_before_today_utc(self):
        df = pd.DataFrame({"QQQ": 1.0, "PSQ": 1.0}, index=pd.to_datetime(["2026-10-19", "2026-10-20", "2026-10-21"]))
        kept = drop_incomplete(df, datetime(2026, 10, 21, 0, 15, tzinfo=timezone.utc))
        self.assertEqual(list(kept.index.strftime("%Y-%m-%d")), ["2026-10-19", "2026-10-20"])

    def test_trim_tail_ends_at_last_complete_qqq_psq_bar(self):
        df = pd.DataFrame({"QQQ": [1.0, 1.0, 1.0], "PSQ": [1.0, 1.0, np.nan]}, index=pd.to_datetime(["2026-10-19", "2026-10-20", "2026-10-21"]))
        self.assertEqual(str(trim_tail(df).index.max().date()), "2026-10-20")

    def test_splice_pins_history_and_rescales_new_rows(self):
        idx = pd.bdate_range("2026-09-24", "2026-10-02")
        old = pd.DataFrame({"A": np.linspace(100, 105, len(idx))}, index=idx).iloc[:-2]
        new = pd.DataFrame({"A": np.linspace(100, 105, len(idx)) * 0.97}, index=idx)         # later dividend rescaled the whole series
        out = splice(old, new, end="2026-09-30")
        np.testing.assert_allclose(out.loc[:"2026-09-30", "A"].values, old.loc[:"2026-09-30", "A"].values)
        np.testing.assert_allclose(out.loc["2026-10-02", "A"], 105.0, rtol=1e-12)
        self.assertEqual(history_drift(old, new, end="2026-09-30"), dict(returns={}, rows_changed=0))

    @unittest.skipUnless(HAS_SNAPSHOT, "price snapshot data/ndx_momentum/prices.csv.gz not present")
    def test_snapshot_reproduces_the_repos_published_backtests(self):
        from ndx_momentum.data import load_prices
        prices = load_prices()
        runs = {u: strategy.backtest(prices, u, end=REPO_END) for u in ("static", "pit")}
        static, pit = (strategy.stats(r["values"], r["dates"]) for r in runs.values())
        self.assertEqual(static["weeks"], 255)
        self.assertAlmostEqual(static["total_return_pct"], 111.4, delta=0.1)       # repo replication notes: +111.4% / 15.9% / 1.27 / -12.8%
        self.assertAlmostEqual(static["max_drawdown_pct"], -12.8, delta=0.1)
        self.assertAlmostEqual(pit["total_return_pct"], 33.2, delta=0.1)           # backtest_pit README: +33.2% / 5.8% / 0.57 / -17.1%
        self.assertAlmostEqual(pit["max_drawdown_pct"], -17.1, delta=0.1)

    @unittest.skipUnless(HAS_SNAPSHOT, "price snapshot data/ndx_momentum/prices.csv.gz not present")
    def test_live_book_uses_only_current_members_and_the_weekly_grid(self):
        from ndx_momentum.data import load_prices
        prices = load_prices()
        book = strategy.current_book(prices, "pit", lag=1)
        dates = strategy.calendar(prices)
        self.assertEqual((dates.index(book["decided_at"]) - LOOKBACK) % HOLD, 0)
        self.assertTrue(set(p["ticker"] for p in book["picks"]) <= PIT().members(book["decided_at"]))
        self.assertAlmostEqual(sum(p["weight"] for p in book["picks"]) + book["hedge"]["weight"], 1.0, places=9)


if __name__ == "__main__":
    unittest.main()
