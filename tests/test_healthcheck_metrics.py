"""Tests for healthcheck_metrics.py."""
from __future__ import annotations

import pytest

import audit
import circuit
import metrics
import retention
import healthcheck_metrics as hm


@pytest.fixture(autouse=True)
def _reset():
    """Reset global state before every test."""
    hm._BREAKER = None
    metrics._counters.clear()  # type: ignore[attr-defined]
    audit._entries.clear()  # type: ignore[attr-defined]
    yield
    hm._BREAKER = None
    metrics._counters.clear()  # type: ignore[attr-defined]
    audit._entries.clear()  # type: ignore[attr-defined]


def test_build_health_metrics_has_required_keys():
    result = hm.build_health_metrics()
    assert "counters" in result
    assert "audit" in result
    assert "circuit_breaker" in result


def test_counters_reflect_increments():
    metrics.increment("deploys_total")
    metrics.increment("deploys_total")
    result = hm.build_health_metrics()
    assert result["counters"]["deploys_total"] == 2


def test_circuit_summary_empty_without_configure():
    result = hm.build_health_metrics()
    assert result["circuit_breaker"] == {}


def test_configure_attaches_breaker():
    cb = circuit.CircuitBreaker(threshold=3, recovery_timeout=30)
    hm.configure(cb)
    assert hm._BREAKER is cb


def test_circuit_summary_shows_known_refs():
    cb = circuit.CircuitBreaker(threshold=2, recovery_timeout=10)
    hm.configure(cb)
    # Trigger the breaker enough to record a ref.
    try:
        cb.check("main")
    except Exception:
        pass
    cb.record_failure("main")
    result = hm.build_health_metrics()
    # After one failure the ref exists in the breaker.
    assert "main" in result["circuit_breaker"].get("refs", {})


def test_audit_stats_in_result():
    """audit stats dict is present even when empty."""
    result = hm.build_health_metrics()
    assert isinstance(result["audit"], dict)


def test_configure_replaces_previous_breaker():
    cb1 = circuit.CircuitBreaker(threshold=2, recovery_timeout=10)
    cb2 = circuit.CircuitBreaker(threshold=5, recovery_timeout=60)
    hm.configure(cb1)
    hm.configure(cb2)
    assert hm._BREAKER is cb2
