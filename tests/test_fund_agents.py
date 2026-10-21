"""Validate the ensemble migration, independent risk and intention-only boundary."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from fund_agents.__main__ import demo_prices, load_config, load_prices, ROOT
from fund_agents.coordinator import FundCoordinator
from fund_agents.ensemble import EnsemblePM
from fund_agents.evidence import fingerprint
from fund_agents.models import FundConfig, FundSnapshot, Holding
from fund_agents.risk import FundRisk
from fund_agents.store import FundStore


class FundAgentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = FundConfig()
        cls.as_of = "2026-10-16"
        cls.prices, cls.source = demo_prices(cls.cfg, cls.as_of)
        cls.snapshot = FundSnapshot.initial(cls.cfg, cls.as_of)
        cls.proposal = EnsemblePM(cls.cfg).propose(cls.prices, cls.snapshot, source_sha256=cls.source)

    def run_cycle(self, prices=None, snapshot=None, config=None, store=None, **kwargs):
        owned = store is None
        store = store or FundStore(":memory:")
        try:
            return FundCoordinator(config or self.cfg, store).run(self.prices if prices is None else prices,
                     snapshot or self.snapshot, source_sha256=self.source, input_basis="SYNTHETIC_DEMO", **kwargs)
        finally:
            if owned:
                store.close()

    def test_three_engines_replace_standalone_pm_without_fills(self):
        report = self.run_cycle()
        self.assertEqual(report["schema_version"], "ensemble-fund-v3")
        self.assertEqual(set(report["pm_proposals"]), {"ensemble"})
        self.assertEqual(report["pm_proposals"]["ensemble"]["status"], "READY")
        self.assertEqual(set(report["pm_proposals"]["ensemble"]["diagnostics"]["engines"]), {"trend", "momentum", "mean_reversion"})
        self.assertEqual(report["portfolio_before"], report["portfolio_after"])
        self.assertEqual(report["fund_risk"]["metrics"]["filled_orders"], 0)
        self.assertEqual(report["committee_chair"]["status"], "NOT_REQUESTED")
        self.assertEqual(report["execution_receipts"][0]["intent"]["execution_condition"], "PORTFOLIO_BASKET_RECORD_ONLY")
        self.assertFalse((ROOT / "fund_agents/pairs.py").exists())

    def test_allocations_and_engine_weights_use_the_selected_policy(self):
        for method in ("regime", "equal_weight", "risk_parity"):
            cfg = replace(self.cfg, allocation_method=method)
            proposal = EnsemblePM(cfg).propose(self.prices, self.snapshot, source_sha256=self.source)
            self.assertEqual(proposal.status, "READY")
            d = proposal.diagnostics
            self.assertAlmostEqual(sum(d["allocations"].values()), 1)
            if method == "regime":
                self.assertEqual(d["allocations"]["mean_reversion"], 0)
            else:
                self.assertGreater(d["allocations"]["mean_reversion"], 0)
            budget = self.cfg.ensemble_budget_usd
            for leg in proposal.groups[0].legs:
                expected = sum(d["allocations"][key] * engine["target_weights"][leg.symbol] for key, engine in d["engines"].items())
                self.assertAlmostEqual(leg.units * leg.price_usd / budget, expected)

    def test_future_prices_do_not_change_an_earlier_target(self):
        future = pd.DataFrame(999999.0, index=pd.DatetimeIndex(["2026-10-19"]), columns=self.prices.columns)
        proposal = EnsemblePM(self.cfg).propose(pd.concat([self.prices, future]), self.snapshot, source_sha256="different-file")
        self.assertEqual(proposal.groups, self.proposal.groups)
        self.assertEqual(proposal.diagnostics["data_sha256"], self.proposal.diagnostics["data_sha256"])

    def test_missing_stale_duplicate_and_nonfinite_required_data_hold(self):
        bad = self.prices.copy(); bad.iloc[-1, 0] = np.nan
        for frame in (self.prices.iloc[:-1], self.prices.drop(self.prices.index[-10]), pd.concat([self.prices, self.prices.tail(1)]), bad):
            report = self.run_cycle(prices=frame)
            self.assertEqual(report["status"], "INPUT_HOLD")
            self.assertEqual(report["execution_receipts"], [])
            self.assertEqual(report["fund_risk"]["metrics"], {})

    def test_calendar_closed_rows_are_excluded_without_filling_sessions(self):
        weekend = pd.DataFrame(777.0, index=pd.DatetimeIndex(["2026-10-10"]), columns=self.prices.columns)
        frame = pd.concat([self.prices, weekend]).sort_index()
        proposal = EnsemblePM(self.cfg).propose(frame, self.snapshot, source_sha256=self.source)
        self.assertEqual(proposal.groups, self.proposal.groups)
        self.assertEqual(proposal.diagnostics["excluded_non_session_rows"], 1)

    def test_risk_scales_the_whole_portfolio_and_enforces_name_caps(self):
        cfg = replace(self.cfg, maximum_name_gross=.001)
        decision = FundRisk(cfg).review((self.proposal,), self.snapshot)
        scale = decision["reviews"][0]["scale"]
        self.assertLess(scale, 1)
        for before, after in zip(self.proposal.groups[0].legs, decision["approved_groups"][0]["legs"]):
            self.assertAlmostEqual(after["units"], before.units * scale)
            self.assertLessEqual(abs(after["units"] * after["price_usd"]), cfg.maximum_name_gross * cfg.initial_nav_usd + 1e-6)
        phantom = decision["phantom_book"]
        self.assertAlmostEqual(phantom["throttled_gross_usd"], phantom["proposed_gross_usd"] - phantom["approved_gross_usd"])

    def test_drawdown_throttle_and_persistent_breaker(self):
        soft = replace(self.snapshot, peak_nav_usd=self.cfg.initial_nav_usd / .85)
        decision = FundRisk(self.cfg).review((self.proposal,), soft)
        self.assertIn("SOFT_DRAWDOWN_THROTTLE", decision["alerts"])
        store = FundStore(":memory:")
        try:
            broken = replace(self.snapshot, peak_nav_usd=self.cfg.initial_nav_usd / .70)
            report = self.run_cycle(snapshot=broken, store=store)
            self.assertEqual(report["status"], "BREAKER_LATCHED")
            self.assertEqual(report["fund_risk"]["metrics"]["target_gross_usd"], 0)
            again = self.run_cycle(store=store)
            self.assertEqual(again["status"], "BREAKER_LATCHED")
        finally:
            store.close()

    def test_closed_market_retains_confirmed_units(self):
        snapshot = replace(self.snapshot, as_of="2026-10-17", holdings=(Holding("ensemble", "portfolio", "V", 100, 100),))
        report = self.run_cycle(snapshot=snapshot)
        self.assertEqual(report["execution_receipts"], [])
        group = report["fund_risk"]["approved_groups"][0]
        self.assertFalse(group["actionable"])
        self.assertEqual(next(l["units"] for l in group["legs"] if l["symbol"] == "V"), 100)

    def test_exact_approval_snapshot_and_idempotent_intentions(self):
        store = FundStore(":memory:")
        try:
            first = self.run_cycle(store=store)
            second = self.run_cycle(store=store)
            self.assertEqual(first["execution_receipts"][0]["intent_id"], second["execution_receipts"][0]["intent_id"])
            self.assertEqual(second["execution_receipts"][0]["status"], "ALREADY_RECORDED_NOT_EXECUTED")
            changed = json.loads(json.dumps(first["fund_risk"]))
            changed["approved_groups"][0]["legs"][0]["units"] += 1
            with self.assertRaises(ValueError):
                store.record(changed, self.snapshot)
            with self.assertRaises(ValueError):
                store.record(first["fund_risk"], replace(self.snapshot, central_cash_usd=1))
            self.assertEqual(store.connection.execute("SELECT COUNT(*) FROM fund_intents").fetchone()[0], 1)
        finally:
            store.close()

    def test_old_accounts_configuration_and_response_roles_are_rejected(self):
        with self.assertRaises(ValueError):
            Holding("pairs", "V~MA", "V", 1, 100)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.json"
            path.write_text(json.dumps({"pairs_budget_usd": 1500000}))
            with self.assertRaises(ValueError):
                load_config(path)
        with self.assertRaises(ValueError):
            self.run_cycle(pm_responses={"pairs": {}})
        store = FundStore(":memory:")
        try:
            store.save_state(self.cfg.account_key, {"fund": {"last_session": None}})
            with self.assertRaises(ValueError):
                self.run_cycle(store=store)
        finally:
            store.close()

    def test_duplicate_raw_csv_headers_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prices.csv"
            path.write_text("Date,V,V\n2026-10-16,100,100\n")
            with self.assertRaises(ValueError):
                load_prices(path)

    def test_llm_reply_cannot_change_quantitative_decisions(self):
        baseline = self.run_cycle()
        envelope = {"tool_names": ["inspect_signals"], "reply": {"model": "test-model", "input_sha256": "wrong-digest", "output": {}}}
        reply = self.run_cycle(pm_responses={"ensemble": envelope})
        self.assertEqual(baseline["fund_risk"], reply["fund_risk"])
        self.assertEqual(reply["pm_representatives"]["ensemble"]["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
