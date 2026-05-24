"""Tests for drain.py"""

from __future__ import annotations

import threading
import time

import pytest

from drain import DeployDrain, DrainTimeout


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_invalid_timeout_raises():
    with pytest.raises(ValueError):
        DeployDrain(timeout=0)


def test_negative_timeout_raises():
    with pytest.raises(ValueError):
        DeployDrain(timeout=-5)


# ---------------------------------------------------------------------------
# acquire / release
# ---------------------------------------------------------------------------

def test_in_flight_starts_at_zero():
    d = DeployDrain()
    assert d.in_flight == 0


def test_acquire_increments_in_flight():
    d = DeployDrain()
    d.acquire()
    assert d.in_flight == 1
    d.release()


def test_release_decrements_in_flight():
    d = DeployDrain()
    d.acquire()
    d.acquire()
    d.release()
    assert d.in_flight == 1
    d.release()


def test_release_never_goes_negative():
    d = DeployDrain()
    d.release()  # extra release
    assert d.in_flight == 0


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

def test_context_manager_acquires_and_releases():
    d = DeployDrain()
    with d:
        assert d.in_flight == 1
    assert d.in_flight == 0


def test_context_manager_releases_on_exception():
    d = DeployDrain()
    try:
        with d:
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert d.in_flight == 0


# ---------------------------------------------------------------------------
# Drain
# ---------------------------------------------------------------------------

def test_drain_returns_immediately_when_idle():
    d = DeployDrain()
    d.drain(timeout=2)  # no in-flight — should return at once


def test_drain_waits_for_in_flight_to_finish():
    d = DeployDrain()
    d.acquire()

    def _finish():
        time.sleep(0.05)
        d.release()

    threading.Thread(target=_finish, daemon=True).start()
    d.drain(timeout=2)
    assert d.in_flight == 0


def test_drain_raises_on_timeout():
    d = DeployDrain(timeout=1)
    d.acquire()  # never released
    with pytest.raises(DrainTimeout):
        d.drain(timeout=1)


def test_acquire_raises_while_draining():
    d = DeployDrain()
    d.drain()  # mark as draining (idle immediately)
    with pytest.raises(RuntimeError, match="draining"):
        d.acquire()


def test_is_draining_false_initially():
    d = DeployDrain()
    assert d.is_draining is False


def test_is_draining_true_after_drain_called():
    d = DeployDrain()
    d.drain()
    assert d.is_draining is True
