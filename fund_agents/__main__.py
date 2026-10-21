"""Run the three-engine Ensemble PM through fund risk and advisory review."""
import argparse
import csv
from dataclasses import fields
from datetime import datetime, timezone
import hashlib
from io import BytesIO, StringIO
import json
from pathlib import Path
import exchange_calendars as xcals
import numpy as np
import pandas as pd
from .coordinator import FundCoordinator
from .evidence import fingerprint
from .models import FundConfig, FundSnapshot, Holding, date
from .store import FundStore

ROOT = Path(__file__).resolve().parents[1]
DEMO_AS_OF = "2026-10-16"


def load_config(path):
    values = json.loads(Path(path).read_text(encoding="utf-8"))
    unknown = set(values) - {f.name for f in fields(FundConfig)}
    if unknown:
        raise ValueError("unknown fund config fields: " + str(sorted(unknown)))
    if "universe" in values:
        values["universe"] = tuple(values["universe"])
    return FundConfig(**values)


def rooted(path):
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def load_portfolio(path):
    values = json.loads(Path(path).read_text(encoding="utf-8"))
    values["holdings"] = tuple(Holding(**h) for h in values.get("holdings", []))
    return FundSnapshot(**values)


def load_prices(path):
    raw = Path(path).read_bytes()
    header = next(csv.reader(StringIO(raw.decode("utf-8-sig"))))
    if len(header) != len(set(header)):
        raise ValueError("equity price columns must be unique")
    prices = pd.read_csv(BytesIO(raw), index_col=0)
    prices.index = pd.to_datetime(prices.index, errors="raise")
    return prices, hashlib.sha256(raw).hexdigest()


def demo_prices(config, as_of):
    calendar = xcals.get_calendar(config.calendar, start="2024-01-01", end="2027-01-01")
    sessions = calendar.sessions_in_range("2024-01-02", as_of)[-240:]
    rng = np.random.default_rng(42)
    market = rng.normal(0.0005, 0.006, len(sessions))
    values = {symbol: 100 * np.exp(np.cumsum(market + rng.normal(0, 0.004, len(sessions)))) for symbol in config.universe}
    values[config.benchmark] = 100 * np.exp(np.cumsum(market))
    frame = pd.DataFrame(values, index=sessions)
    return frame, fingerprint({"basis": "SYNTHETIC_DEMO", "dates": sessions.strftime("%Y-%m-%d").tolist(), "prices": frame.to_numpy().tolist()})


def export_reports(report, directory):
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / (report["cycle_id"] + ".json")
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    rows = [{"fund_as_of": report["as_of"], "pm": pm, "group": group["group"], "symbol": leg["symbol"], "price_usd": leg["price_usd"], "price_session": group["signal_session"], "market_closed": not group["actionable"]} for pm, proposal in report["pm_proposals"].items() for group in proposal["groups"] for leg in group["legs"]]
    pd.DataFrame(rows, columns=["fund_as_of", "pm", "group", "symbol", "price_usd", "price_session", "market_closed"]).to_csv(destination.with_suffix(".closing_prices.csv"), index=False)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/fund_agents.demo.json")
    parser.add_argument("--as-of", help="Valuation date; required exchange sessions must have closed")
    parser.add_argument("--prices", type=Path, help="Local USD equity closes indexed by session date")
    parser.add_argument("--benchmark-prices", type=Path, help="Benchmark CSV if absent from --prices")
    parser.add_argument("--sectors", type=Path, help="Optional CSV with Ticker and Sector for sector-neutral momentum")
    parser.add_argument("--portfolio", type=Path, help="Confirmed ensemble account snapshot")
    parser.add_argument("--pm-responses", type=Path, help="Optional ensemble and chair diagnostic selections and imported LLM replies")
    args = parser.parse_args()
    try:
        cfg = load_config(args.config)
        sectors = None
        if args.sectors:
            frame = pd.read_csv(args.sectors)
            if not {"Ticker", "Sector"}.issubset(frame.columns) or frame.Ticker.duplicated().any() or frame[["Ticker", "Sector"]].isna().any().any():
                raise ValueError("sector CSV requires unique Ticker values and nonempty Sector values")
            sectors = dict(zip(frame.Ticker.astype(str), frame.Sector.astype(str)))
        if cfg.mode == "demo":
            if any((args.as_of, args.prices, args.benchmark_prices, args.portfolio, args.sectors)):
                parser.error("demo generates synthetic inputs; use research mode for supplied inputs")
            as_of = DEMO_AS_OF
            prices, source = demo_prices(cfg, as_of)
            basis = "SYNTHETIC_DEMO"
        else:
            if not args.as_of or not args.prices:
                parser.error("research requires --as-of and --prices")
            as_of = args.as_of
            cutoff = date(as_of)
            now = pd.Timestamp(datetime.now(timezone.utc))
            if cutoff.date() > now.date():
                raise ValueError("as_of cannot be a future date")
            calendar = xcals.get_calendar(cfg.calendar, start=str((cutoff - pd.Timedelta(days=14)).date()), end=str((cutoff + pd.Timedelta(days=32)).date()))
            session = calendar.date_to_session(cutoff, direction="previous")
            if calendar.session_close(session).tz_convert("UTC") > now:
                raise ValueError("the latest required exchange session has not closed")
            prices, source = load_prices(args.prices)
            if cfg.benchmark not in prices.columns:
                if not args.benchmark_prices:
                    raise ValueError("provide --benchmark-prices or include " + cfg.benchmark + " in --prices")
                bench, bench_source = load_prices(args.benchmark_prices)
                column = cfg.benchmark if cfg.benchmark in bench else "Close"
                if column not in bench:
                    raise ValueError("benchmark CSV requires the benchmark ticker or Close column")
                prices = prices.join(bench[[column]].rename(columns={column: cfg.benchmark}), how="left", validate="one_to_one")
                source = fingerprint({"equities": source, "benchmark": bench_source})
            basis = "HISTORICAL_RESEARCH"
        snapshot = load_portfolio(args.portfolio) if args.portfolio else FundSnapshot.initial(cfg, as_of)
        if snapshot.as_of != as_of:
            raise ValueError("portfolio date must match --as-of")
        responses = json.loads(args.pm_responses.read_text(encoding="utf-8")) if args.pm_responses else None
        store = FundStore(rooted(cfg.state_path))
        try:
            report = FundCoordinator(cfg, store).run(prices, snapshot, source_sha256=source, input_basis=basis, sector_mapping=sectors, pm_responses=responses)
        finally:
            store.close()
        destination = export_reports(report, rooted(cfg.report_directory))
        print(json.dumps({"status": report["status"], "mode": cfg.mode, "report": str(destination), "pm_status": {k: v["status"] for k, v in report["pm_proposals"].items()}, "marked_nav_usd": report["fund_risk"]["metrics"].get("marked_nav_usd"), "intention_groups": len(report["execution_receipts"]), "fills": 0}, indent=2))
        return 2 if report["status"] in ("INPUT_HOLD", "RISK_VETO", "BREAKER_LATCHED") else 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
        print(json.dumps({"status": "INPUT_HOLD", "error": str(exc), "fills": 0}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
