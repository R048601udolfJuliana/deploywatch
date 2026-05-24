"""HTTP handler that exposes dependency health checks at GET /deps."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from typing import List, Dict

from depcheck import run_checks, DepReport

_CHECKS: List[Dict] = []


def configure(checks: List[Dict]) -> None:
    """Set the list of check descriptors used by the handler."""
    global _CHECKS
    _CHECKS = list(checks)


def _get_checks() -> List[Dict]:
    return _CHECKS


def make_dep_handler() -> type:
    """Return a BaseHTTPRequestHandler subclass for /deps."""

    class DepHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/deps":
                self.send_response(404)
                self.end_headers()
                return

            report: DepReport = run_checks(_get_checks())
            body = json.dumps(report.to_dict(), indent=2).encode()
            status = 200 if report.all_ok else 503

            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:  # pragma: no cover
            pass  # silence default stderr logging

    return DepHandler


DepHandler = make_dep_handler()
