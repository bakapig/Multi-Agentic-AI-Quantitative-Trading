"""Read-only, localhost dashboard for saved fund coordinator reports.

Run with ``python -m fund_agents.dashboard``. No trading engine is invoked.
"""

import argparse
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from .investor import build_investor_data


ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).with_name("web")


def reject_constant(value):
    raise ValueError("non-finite JSON number: " + value)


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        reject_constant(value)
    return number


def reports_in(directory):
    """Index only complete report envelopes, never quality audits or other JSON."""
    reports = []
    warnings = []
    for path in directory.rglob("*.json"):
        if path.name.endswith(".quality.json"):
            continue
        try:
            if not path.resolve().is_relative_to(directory.resolve()):
                continue
            report = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant, parse_float=finite_float)
            if not isinstance(report, dict) or report.get("schema_version") != "ensemble-fund-v3":
                continue
            for key in ("config", "fund_risk", "pm_proposals", "portfolio_before"):
                if not isinstance(report.get(key), dict):
                    raise ValueError("incomplete report: " + key)
            if set(report["pm_proposals"]) != {"ensemble"}:
                raise ValueError("active portal requires exactly the Ensemble PM")
            if not all(isinstance(report.get(k), str) and report[k]
                       for k in ("cycle_id", "as_of", "generated_at_utc", "mode", "status")):
                raise ValueError("missing report identity")
            reports.append((path.relative_to(directory).as_posix(), report))
        except (ValueError, OSError) as exc:
            warnings.append(f"Skipped {path.name}: {exc}")
    reports.sort(key=lambda item: (item[1]["generated_at_utc"], item[0]), reverse=True)
    return reports, warnings


class DashboardHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, report_directory, backtest_directory=None, **kwargs):
        self.report_directory = report_directory
        self.backtest_directory = backtest_directory or ROOT / 'reports/october_2026'
        super().__init__(*args, **kwargs)

    def respond(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def json_response(self, status, data):
        self.respond(status, json.dumps(data, allow_nan=False).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == '/api/investor':
            reports, _ = reports_in(self.report_directory)
            replay = next((r for _, r in reports if r['mode'] == 'research'
                           and r['status'] == 'INTENTS_RECORDED'), None)
            try:
                self.json_response(200, build_investor_data(self.backtest_directory, replay))
            except (ValueError, KeyError, OSError, TypeError):
                self.json_response(503, {'error': 'Ensemble research evidence is unavailable. Refresh after the source is repaired.'})
            return
        assets = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                  "/styles.css": ("styles.css", "text/css")}
        if url.path not in assets:
            self.json_response(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        filename, mime = assets[url.path]
        self.respond(200, (STATIC / filename).read_bytes(), mime + "; charset=utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    parser.add_argument("--reports", type=Path, default=ROOT / "runs/fund_agents")
    parser.add_argument("--backtest", type=Path, default=ROOT / "reports/october_2026")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), partial(DashboardHandler, report_directory=args.reports.resolve(), backtest_directory=args.backtest.resolve()))
    print(f"AlphaHunt Capital: http://{args.host}:{server.server_port} (ensemble research)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
