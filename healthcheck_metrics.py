"""Expose metrics and circuit-breaker state in the health endpoint."""
from __future__ import annotations

from typing import Any, Dict

import audit
import circuit
import metrics
import retention

_BREAKER: circuit.CircuitBreaker | None = None


def configure(breaker: circuit.CircuitBreaker) -> None:
    """Attach a CircuitBreaker instance used by the health summary."""
    global _BREAKER
    _BREAKER = breaker


def _circuit_summary() -> Dict[str, Any]:
    if _BREAKER is None:
        return {}
    statuses: Dict[str, str] = {}
    # Expose status for every ref tracked by the breaker.
    for ref, state in _BREAKER._refs.items():  # type: ignore[attr-defined]
        statuses[ref] = state.status
    return {"refs": statuses}


def build_health_metrics() -> Dict[str, Any]:
    """Return a dict suitable for embedding in the /health response."""
    snap = metrics.snapshot()
    audit_stats = retention.stats()
    return {
        "counters": snap.to_dict(),
        "audit": audit_stats,
        "circuit_breaker": _circuit_summary(),
    }
