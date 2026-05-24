"""Tests for circuit.py"""
import time
import pytest
from circuit import CircuitBreaker, CircuitOpenError, _CLOSED, _OPEN, _HALF_OPEN


@pytest.fixture()
def cb() -> CircuitBreaker:
    return CircuitBreaker(threshold=3, recovery_timeout=60.0)


def test_invalid_threshold_raises():
    with pytest.raises(ValueError, match="threshold"):
        CircuitBreaker(threshold=0)


def test_invalid_recovery_timeout_raises():
    with pytest.raises(ValueError, match="recovery_timeout"):
        CircuitBreaker(threshold=1, recovery_timeout=0)


def test_check_passes_for_unknown_ref(cb):
    cb.check("refs/heads/main")  # should not raise


def test_status_closed_initially(cb):
    assert cb.status("refs/heads/main") == _CLOSED


def test_failures_below_threshold_do_not_open(cb):
    ref = "refs/heads/main"
    cb.record_failure(ref)
    cb.record_failure(ref)
    assert cb.status(ref) == _CLOSED
    cb.check(ref)  # should not raise


def test_reaching_threshold_opens_circuit(cb):
    ref = "refs/heads/main"
    for _ in range(3):
        cb.record_failure(ref)
    assert cb.status(ref) == _OPEN


def test_open_circuit_raises_on_check(cb):
    ref = "refs/heads/main"
    for _ in range(3):
        cb.record_failure(ref)
    with pytest.raises(CircuitOpenError) as exc_info:
        cb.check(ref)
    assert exc_info.value.ref == ref
    assert exc_info.value.retry_in > 0


def test_circuit_open_error_message(cb):
    ref = "refs/heads/feature"
    for _ in range(3):
        cb.record_failure(ref)
    with pytest.raises(CircuitOpenError, match=ref):
        cb.check(ref)


def test_success_resets_circuit(cb):
    ref = "refs/heads/main"
    for _ in range(3):
        cb.record_failure(ref)
    cb.record_success(ref)
    assert cb.status(ref) == _CLOSED
    cb.check(ref)  # should not raise


def test_manual_reset_clears_open_circuit(cb):
    ref = "refs/heads/main"
    for _ in range(3):
        cb.record_failure(ref)
    cb.reset(ref)
    assert cb.status(ref) == _CLOSED
    cb.check(ref)  # should not raise


def test_reset_unknown_ref_is_noop(cb):
    cb.reset("refs/heads/nonexistent")  # should not raise


def test_half_open_after_recovery_timeout(monkeypatch):
    cb = CircuitBreaker(threshold=2, recovery_timeout=1.0)
    ref = "refs/heads/main"
    cb.record_failure(ref)
    cb.record_failure(ref)
    assert cb.status(ref) == _OPEN

    # Simulate time passing beyond recovery window
    original_monotonic = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: original_monotonic() + 2.0)

    cb.check(ref)  # should not raise; transitions to half-open
    assert cb.status(ref) == _HALF_OPEN


def test_independent_refs_do_not_affect_each_other(cb):
    ref_a = "refs/heads/main"
    ref_b = "refs/heads/staging"
    for _ in range(3):
        cb.record_failure(ref_a)
    cb.check(ref_b)  # ref_b should still be fine
    assert cb.status(ref_b) == _CLOSED
