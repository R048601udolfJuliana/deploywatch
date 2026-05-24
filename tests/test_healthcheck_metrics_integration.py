"""Integration tests: healthcheck_metrics wired with real subsystems."""
from __future__ import annotations

import datetime
import pytest

import audit
import circuit
import metrics
import retention
import healthcheck_metrics as hm


@pytest.fixture(autouse=True)
def _reset_all():
    hm._BREAKER = None
    metrics._counters.clear()  # type: ignore[attr-defined]
    audit._entries.clear()  # type: ignore[attr-defined]
    yield
    hm._BREAKER = None
    metrics._counters.clear()  # type: ignore[attr-defined]
    audit._entries.clear()  # type: ignore[attr-defined]


def _ts(offset_seconds: int = 0) -> datetime.datetime:
    return datetime.datetime.utcnow() - datetime.timedelta(seconds=offset_seconds)


def test_full_snapshot_is_json_serialisable():
    import json

    cb = circuit.CircuitBreaker(threshold=3, recovery_timeout=30)
    hm.configure(cb)
    metrics.increment("deploys_total", 5)
    metrics.increment("deploys_failed", 1)
    audit.record("refs/heads/main", "abc123", True, "deploy.sh")

    result = hm.build_health_metrics()
    serialised = json.dumps(result)  # must not raise
    assert "deploys_total" in serialised


def test_open_circuit_reflected_in_health():
    cb = circuit.CircuitBreaker(threshold=2, recovery_timeout=60)
    hm.configure(cb)
    # Record enough failures to open the circuit.
    cb.record_failure("refs/heads/release")
    cb.record_failure("refs/heads/release")

    result = hm.build_health_metrics()
    refs = result["circuit_breaker"].get("refs", {})
    assert refs.get("refs/heads/release") == "open"


def test_audit_count_matches_seeded_entries():
    for i in range(4):
        audit.record("refs/heads/main", f"sha{i}", True, "deploy.sh")

    result = hm.build_health_metrics()
    total = result["audit"].get("total", 0)
    assert total == 4
