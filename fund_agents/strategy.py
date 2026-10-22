"""Record the ensemble's upstream attribution, local engine hashes and policy."""
from dataclasses import asdict
import hashlib
from pathlib import Path


def strategy_evidence(config):
    root = Path(__file__).resolve().parents[1]
    names = ("trend_strategy.py", "momentum_strategy.py", "reversion_strategy.py", "regime_detector.py")
    hashes = {name: hashlib.sha256((root / "multi_strategy_ensemble" / name).read_bytes()).hexdigest() for name in names}
    hashes["fund_adapter"] = hashlib.sha256(Path(__file__).with_name("ensemble.py").read_bytes()).hexdigest()
    policy = asdict(config)
    return {"repository": "https://github.com/bakapig/Multi-Agentic-AI-Quantitative-Trading",
            "upstream_commit": "55da4237b7eaeb036927a18da7b273c3e42034cd",
            "engine_files_sha256": hashes, "policy": policy,
            "components": ["Trend following", "Momentum", "Mean reversion"],
            "adaptations": ["Expose closing-session targets from the existing research engines",
                            "Aggregate symbol weights into one Ensemble PM portfolio",
                            "Validate complete USD equity sessions without filling missing prices",
                            "Independent fund risk; record-only intentions; zero fills"]}
