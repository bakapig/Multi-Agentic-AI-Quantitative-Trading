import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

HAS_SCIPY = importlib.util.find_spec("scipy") is not None
if HAS_SCIPY:
    from momentum import live, strategy
    from momentum.config import DATA, SEEN_END
    from momentum.data import download, rf_daily, weekday_panel
    from momentum.garch import fit

FIXTURE = Path(__file__).parent / "fixtures" / "momentum_golden_net.csv"


def simulate(n, seed, a0=0.05, a1=0.10, b1=0.85):
    rng, h, e = np.random.default_rng(seed), a0 / (1 - a1 - b1), []
    for _ in range(n):
        x = np.sqrt(h) * rng.standard_t(8) * np.sqrt(6 / 8)
        e.append(x)
        h = a0 + a1 * x * x + b1 * h
    return np.array(e)


def prices_from(e, start="2020-01-01"):
    return pd.Series(100 * np.exp(np.cumsum(e) / 100), index=pd.bdate_range(start, periods=len(e) + 1)[1:])


@unittest.skipUnless(HAS_SCIPY, "scipy is not installed (see requirements-momentum.txt)")
class MomentumStrategyTests(unittest.TestCase):
    def test_garch_t_fit_is_stationary_and_in_bounds(self):
        par = fit(simulate(2000, 1))
        a0, a1, b1, nu = par
        self.assertLess(a1 + b1, 1.0)
        self.assertTrue(0.05 < a1 < 0.3 and 0.6 < b1 < 0.95 and 2.5 <= nu <= 60)

    def test_incremental_garch_matches_full_refit(self):
        raw = pd.DataFrame({"A": prices_from(simulate(420, 2)), "B": prices_from(simulate(420, 3, 0.1, 0.08, 0.88))})
        with mock.patch.object(strategy, "GARCH_MIN_OBS", 150), mock.patch.object(strategy, "GARCH_WINDOW", 300), mock.patch.object(strategy, "REFIT_EVERY", 40):
            full = strategy.garch_vol_forecasts(raw)
            state = {}
            strategy.garch_vol_forecasts(raw.iloc[:350], state=state)
            cache = strategy.garch_vol_forecasts(raw.iloc[:350])
            ext, _ = strategy.extend_garch_forecasts(raw, cache, state)
            full_state = {}
            strategy.garch_vol_forecasts(raw, state=full_state)
        pd.testing.assert_frame_equal(ext.dropna(how="all"), full.dropna(how="all"), rtol=1e-6, atol=1e-9)
        for c in raw:
            self.assertEqual(state[c][0], full_state[c][0])
            np.testing.assert_allclose(state[c][1], full_state[c][1])

    def test_packaged_strategy_reproduces_original_research_returns(self):
        gold = pd.read_csv(FIXTURE, index_col=0, parse_dates=True)
        px, irx = download()
        raw, ff = weekday_panel(px)
        R = strategy.run_blend(ff, strategy.garch_vol_forecasts(raw, DATA / "garch_vol_forecasts.csv"), rf_daily(irx, ff.index))
        got = pd.DataFrame({"net": R["net"], "core": R["core"], "trend": R["trend"]}).reindex(gold.index)
        np.testing.assert_allclose(got.values, gold.values, atol=1e-10, rtol=0)

    def test_weights_do_not_depend_on_future_prices(self):
        px, irx = download()
        raw, ff = weekday_panel(px)
        gv, rf = strategy.garch_vol_forecasts(raw, DATA / "garch_vol_forecasts.csv"), rf_daily(irx, ff.index)
        full = strategy.run_blend(ff, gv, rf)["W"]
        cut = strategy.run_blend(ff.iloc[:-15], gv, rf)["W"]
        np.testing.assert_allclose(full.loc[cut.index].values, cut.values, atol=1e-12)

    def test_drop_incomplete_keeps_only_bars_before_today_utc(self):
        s = pd.Series(1.0, index=pd.to_datetime(["2026-10-19", "2026-10-20", "2026-10-21"]))
        kept = live.drop_incomplete(s, datetime(2026, 10, 21, 0, 15, tzinfo=timezone.utc))
        self.assertEqual(list(kept.index.strftime("%Y-%m-%d")), ["2026-10-19", "2026-10-20"])

    def test_history_drift_ignores_dividend_rescaling_but_flags_revised_returns(self):
        idx = pd.bdate_range("2026-08-03", "2026-09-30")
        old = pd.DataFrame({"A": 100 * np.exp(np.cumsum(simulate(len(idx), 4)) / 100)}, index=idx)
        self.assertEqual(live.history_drift(old, old * 0.97), dict(returns={}, rows_changed=0))
        revised = old.copy()
        revised.iloc[20:] *= 1.01
        self.assertIn("A", live.history_drift(old, revised)["returns"])
        self.assertEqual(live.history_drift(old, old.iloc[1:])["rows_changed"], 1)


if __name__ == "__main__":
    unittest.main()
