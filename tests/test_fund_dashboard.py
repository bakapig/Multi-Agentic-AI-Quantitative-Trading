"""Exercise the read-only report boundary without invoking a trading engine."""

from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fund_agents.dashboard import DashboardHandler, reports_in
from fund_agents.investor import build_investor_data, public_replay


def envelope(cycle="test", generated="2026-10-14T10:00:00+00:00"):
    return {"schema_version": "ensemble-fund-v3", "cycle_id": cycle,
            "as_of": "2026-08-28", "generated_at_utc": generated,
            "mode": "research", "status": "INPUT_HOLD", "config": {},
            "fund_risk": {"status": "INPUT_HOLD", "metrics": {}, "approved_groups": []},
            "pm_proposals": {"ensemble": {"status": "INPUT_HOLD"}}, "portfolio_before": {}}


def backtest_fixture(root):
    root.mkdir(parents=True, exist_ok=True)
    manifest = {'full_original_window': ['2026-10-01', '2026-10-02'],
                'initial_research_capital': 1000, 'requested_xnys_sessions': 2,
                'full_original_assets': 3, 'upstream_reference': 'test-commit'}
    (root / 'run_manifest.json').write_text(json.dumps(manifest))
    headers = 'Date,Regime_Routed_Ensemble,Equal_Weight_1_3,Risk_Parity,Trend_Following,Momentum,Mean_Reversion,Benchmark_SPY\n'
    (root / 'original_full_universe_equity.csv').write_text(headers + '2026-10-01,' + ','.join(['900'] * 7) + '\n2026-10-02,' + ','.join(['950'] * 7) + '\n')
    (root / 'original_full_universe_regimes.csv').write_text('Date,regime,weight_trend,weight_momentum,weight_reversion,weight_cash\n2026-10-01,TRENDING_BULL,.5,.4,0,.1\n2026-10-02,TRENDING_BULL,.5,.4,0,.1\n')


class QuietHandler(DashboardHandler):
    def log_message(self, *args):
        pass


class FundDashboardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def write(self, filename, value):
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_index_excludes_audits_and_preserves_held_metrics(self):
        self.write("research/held.json", envelope())
        self.write("held.quality.json", envelope("not-a-cycle"))
        self.write("unrelated.json", {"private": "not a report"})
        self.write("legacy.json", dict(envelope("legacy"), schema_version="pairs-fund-v2"))
        reports, warnings = reports_in(self.root)
        self.assertEqual([r[0] for r in reports], ["research/held.json"])
        self.assertEqual(reports[0][1]["fund_risk"]["metrics"], {})
        self.assertEqual(warnings, [])

    def test_newest_saved_cycle_first_and_invalid_reports_are_skipped(self):
        self.write("older.json", envelope("older"))
        self.write("newer.json", envelope("newer", "2026-10-15T10:00:00+00:00"))
        self.write("incomplete.json", {"schema_version": "ensemble-fund-v3"})
        (self.root / "partial.json").write_text('{"schema_version":', encoding="utf-8")
        self.write("nonfinite.json", dict(envelope(), config={"limit": float("nan")}))
        (self.root / "overflow.json").write_text(json.dumps(envelope()).replace('"config": {}', '"config": {"limit": 1e999}'), encoding="utf-8")
        self.write("invalid-date-type.json", envelope(generated=100))
        reports, warnings = reports_in(self.root)
        self.assertEqual([r[1]["cycle_id"] for r in reports], ["newer", "older"])
        self.assertEqual(len(warnings), 5)

    def test_empty_or_absent_directory(self):
        self.assertEqual(reports_in(self.root / "missing"), ([], []))

    def test_active_schema_cannot_include_the_retired_pm(self):
        invalid = envelope()
        invalid["pm_proposals"]["pairs"] = {"status": "READY"}
        self.write("mixed.json", invalid)
        reports, warnings = reports_in(self.root)
        self.assertEqual(reports, [])
        self.assertEqual(len(warnings), 1)

    def test_http_serves_only_indexed_reports_and_known_assets(self):
        expected = envelope()
        self.write("research/test.json", expected)
        self.write("legacy.json", dict(envelope(), schema_version="two-pm-fund-v1"))
        before = (self.root / "research/test.json").read_bytes()
        backtest = self.root / 'backtest'
        backtest_fixture(backtest)
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, report_directory=self.root, backtest_directory=backtest))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/api/investor") as response:
                public = json.load(response)
                self.assertEqual(public['brand']['name'], 'AlphaHunt Capital')
                self.assertEqual(public['backtest']['series']['ensemble']['index'], [100, 90, 95])
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            for path in ("/", "/app.js", "/styles.css"):
                with urlopen(base + path) as response:
                    self.assertEqual(response.status, 200)
            for path in ("/api/reports", "/api/report?id=research%2Ftest.json", "/api/report?id=..%2Fsecret.json", "/api/report?id=legacy.json", "/api/report", "/../README.md", "/runtime/fund.sqlite"):
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + path)
                self.assertEqual(error.exception.code, 404)
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base + "/api/report", data=b"{}", method="POST"))
            self.assertEqual(error.exception.code, 501)
            self.assertEqual((self.root / "research/test.json").read_bytes(), before)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_public_curves_preserve_loss_from_starting_base(self):
        backtest_fixture(self.root)
        public = build_investor_data(self.root)
        s = public['backtest']['series']['ensemble']
        self.assertAlmostEqual(s['metrics']['total_return'], -.05)
        self.assertAlmostEqual(s['metrics']['max_drawdown'], -.1)
        self.assertEqual(s['index'], [100, 90, 95])
        self.assertEqual(set(public['backtest']['series']), {'ensemble', 'equal_weight', 'risk_parity', 'trend', 'momentum', 'mean_reversion', 'benchmark'})
        self.assertNotIn('initial_research_capital', json.dumps(public))

    def test_replay_is_scale_invariant_and_discards_private_prose(self):
        replay = dict(envelope(), status='INTENTS_RECORDED',
                      config={'ensemble_budget_usd': 3000000, 'soft_drawdown': .12, 'maximum_drawdown': .25},
                      fund_risk={'metrics': {'marked_nav_usd': 5000000}, 'phantom_book': {
                          'proposed_gross_usd': 2700000, 'approved_gross_usd': 2500000, 'throttled_gross_usd': 200000}},
                      committee_chair={'status': 'NOT_REQUESTED', 'computed_memo': {'summary': 'Private account has $5,000,000'}})
        first = public_replay(replay)
        replay['fund_risk']['metrics']['marked_nav_usd'] *= 10
        for k in replay['fund_risk']['phantom_book']:
            replay['fund_risk']['phantom_book'][k] *= 10
        self.assertEqual(first, public_replay(replay))
        self.assertEqual(first['proposed_gross_fraction'], .54)
        self.assertEqual(first['removed_gross_fraction'], .04)
        serialized = json.dumps(first)
        for token in ('usd', '$', '5000000', '3000000', 'Private account', 'computed_memo'):
            self.assertNotIn(token, serialized)

    def test_incomplete_or_nonfinite_series_cannot_be_published(self):
        backtest_fixture(self.root)
        curve = self.root / 'original_full_universe_equity.csv'
        curve.write_text(curve.read_text().replace('900', 'nan', 1))
        with self.assertRaises(ValueError):
            build_investor_data(self.root)


if __name__ == "__main__":
    unittest.main()
