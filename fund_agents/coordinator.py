"""Coordinate the connected PMs, final risk, execution records and AI evidence."""

from datetime import datetime, timezone
from uuid import uuid4

from .evidence import fingerprint, json_value

from . import __version__
from .ensemble import EnsemblePM
from .representative import CommitteeChairAgent, PMRepresentative
from .risk import FundRisk


class FundCoordinator:
    def __init__(self, config, store):
        self.config, self.store = config, store
        self.ensemble = EnsemblePM(config)
        self.risk = FundRisk(config)

    def run(self, prices, snapshot, *, source_sha256, input_basis, sector_mapping=None, pm_responses=None):
        expected_basis = "SYNTHETIC_DEMO" if self.config.mode == "demo" else "HISTORICAL_RESEARCH"
        if input_basis != expected_basis:
            raise ValueError(f"{self.config.mode} fund requires {expected_basis} equity inputs")
        if not isinstance(source_sha256, str) or not source_sha256.strip():
            raise ValueError("equity inputs require a source digest")
        if pm_responses is not None and (not isinstance(pm_responses, dict) or set(pm_responses) - {"ensemble", "chair"}):
            raise ValueError("PM responses can contain only ensemble and chair envelopes")
        cycle_id = str(uuid4())
        with self.store.transaction():
            context = self.store.state(self.config.account_key) or {}
            if set(context) - {"fund", "schema_version"} or (context and context.get("schema_version") != "ensemble-fund-v3"):
                raise ValueError("legacy fund state requires a separate ensemble account and state path")
            previous = context.get("fund")
            if previous and previous["last_session"] > snapshot.as_of:
                raise ValueError("fund dates cannot run backwards; use a different replay account")
            ensemble = self.ensemble.propose(prices, snapshot, source_sha256=source_sha256, sector_mapping=sector_mapping)
            proposals = (ensemble,)
            decision = self.risk.review(proposals, snapshot, previous)
            self.store.save_decision(decision)
            receipts = self.store.record(decision, snapshot)
            responses = pm_responses or {}
            representatives = {p.pm: PMRepresentative(p, decision).memo(responses.get(p.pm)) for p in proposals}
            chair = CommitteeChairAgent(proposals, decision, representatives).memo(responses.get("chair"))
            state = {"schema_version": "ensemble-fund-v3", "fund": decision["state"]}
            self.store.save_state(self.config.account_key, state)
            status = decision["status"]
            if status == "REVIEWED":
                status = "INTENTS_RECORDED" if receipts else "NO_ACTION"
            report = json_value({
                "schema_version": "ensemble-fund-v3", "architecture_version": __version__, "cycle_id": cycle_id,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(), "as_of": snapshot.as_of,
                "mode": self.config.mode, "execution_mode": "record_only", "status": status,
                "config": self.config, "config_sha256": fingerprint(self.config),
                "portfolio_before": snapshot, "portfolio_after": snapshot,
                "pm_proposals": {p.pm: p for p in proposals}, "fund_risk": decision,
                "execution_receipts": receipts, "pm_representatives": representatives,
                "committee_chair": chair,
                "limitations": [
                    "Execution records portfolio intentions only. No orders, fills, fees charged or changed holdings.",
                    "AI supports imported, digest-checked replies and diagnostic tool selections; no automatic LLM provider calls.",
                    "Ensemble targets are research quantities; executable quotes, board lots, borrow availability and margin require a future fill adapter.",
                    "Supplied snapshots carry confirmed positions. Recorded intents never become next-day holdings.",
                ],
            })
            self.store.save_cycle(cycle_id, self.config.account_key, report)
        return report
