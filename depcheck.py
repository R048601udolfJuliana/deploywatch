"""Dependency health checks for external services used by deploywatch."""

from __future__ import annotations

import socket
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DepStatus:
    name: str
    ok: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass
class DepReport:
    checks: List[DepStatus] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def to_dict(self) -> dict:
        return {
            "all_ok": self.all_ok,
            "checks": [c.to_dict() for c in self.checks],
        }


def check_tcp(name: str, host: str, port: int, timeout: float = 2.0) -> DepStatus:
    """Check that a TCP port is reachable."""
    import time
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency = (time.monotonic() - start) * 1000
            return DepStatus(name=name, ok=True, latency_ms=round(latency, 2))
    except OSError as exc:
        return DepStatus(name=name, ok=False, error=str(exc))


def check_http(name: str, url: str, timeout: float = 3.0) -> DepStatus:
    """Check that an HTTP endpoint returns a 2xx status."""
    import time
    start = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            latency = (time.monotonic() - start) * 1000
            ok = 200 <= resp.status < 300
            return DepStatus(name=name, ok=ok, latency_ms=round(latency, 2),
                             error=None if ok else f"HTTP {resp.status}")
    except urllib.error.URLError as exc:
        return DepStatus(name=name, ok=False, error=str(exc.reason))
    except Exception as exc:  # pragma: no cover
        return DepStatus(name=name, ok=False, error=str(exc))


def run_checks(checks: List[Dict]) -> DepReport:
    """Run a list of check descriptors and return a DepReport.

    Each descriptor must have 'type' ('tcp' or 'http'), 'name', and
    type-specific keys: tcp -> host, port; http -> url.
    """
    results: List[DepStatus] = []
    for spec in checks:
        kind = spec.get("type")
        name = spec.get("name", "unknown")
        if kind == "tcp":
            results.append(check_tcp(name, spec["host"], int(spec["port"]),
                                     timeout=spec.get("timeout", 2.0)))
        elif kind == "http":
            results.append(check_http(name, spec["url"],
                                      timeout=spec.get("timeout", 3.0)))
        else:
            results.append(DepStatus(name=name, ok=False,
                                     error=f"unknown check type: {kind!r}"))
    return DepReport(checks=results)
