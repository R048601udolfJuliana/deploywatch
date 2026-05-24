"""Tests for ratelimit_audit.py."""
from __future__ import annotations

import datetime
import importlib

import pytest

import audit
import ratelimit_audit


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _reset():
    """Clear the in-process audit log between tests."""
    audit._entries.clear()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# record_violation
# ---------------------------------------------------------------------------

def test_record_violation_returns_entry(_reset=None):
    _reset_state()
    entry = ratelimit_audit.record_violation("10.0.0.1")
    assert entry is not None
    assert entry.event == "rate_limit_violation"
    assert entry.success is False


def test_record_violation_stores_client_ip():
    _reset_state()
    entry = ratelimit_audit.record_violation("192.168.1.42", path="/webhook")
    assert entry.detail["client_ip"] == "192.168.1.42"


def test_record_violation_stores_path():
    _reset_state()
    entry = ratelimit_audit.record_violation("1.2.3.4", path="/deploy")
    assert entry.detail["path"] == "/deploy"


def test_record_violation_uses_rl_ref():
    _reset_state()
    entry = ratelimit_audit.record_violation("1.2.3.4")
    assert entry.ref == ratelimit_audit._RL_REF


# ---------------------------------------------------------------------------
# violation_count
# ---------------------------------------------------------------------------

def test_violation_count_zero_when_empty():
    _reset_state()
    assert ratelimit_audit.violation_count() == 0


def test_violation_count_increments_per_call():
    _reset_state()
    ratelimit_audit.record_violation("10.0.0.1")
    ratelimit_audit.record_violation("10.0.0.2")
    assert ratelimit_audit.violation_count() == 2


def test_violation_count_excludes_non_rl_events():
    _reset_state()
    # Seed a non-rate-limit event directly
    audit.record(ref="main", event="deploy", success=True, detail={})
    ratelimit_audit.record_violation("10.0.0.1")
    assert ratelimit_audit.violation_count() == 1


def test_violation_count_respects_since():
    _reset_state()
    past = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    ratelimit_audit.record_violation("10.0.0.1")
    ratelimit_audit.record_violation("10.0.0.2")
    # Only count violations after *now* – should be 0
    future = datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
    assert ratelimit_audit.violation_count(since=future) == 0


# ---------------------------------------------------------------------------
# last_violation
# ---------------------------------------------------------------------------

def test_last_violation_none_when_empty():
    _reset_state()
    assert ratelimit_audit.last_violation() is None


def test_last_violation_returns_most_recent():
    _reset_state()
    ratelimit_audit.record_violation("10.0.0.1")
    ratelimit_audit.record_violation("10.0.0.99")
    last = ratelimit_audit.last_violation()
    assert last is not None
    assert last.detail["client_ip"] == "10.0.0.99"


def test_last_violation_ignores_other_events():
    _reset_state()
    audit.record(ref="main", event="deploy", success=True, detail={})
    assert ratelimit_audit.last_violation() is None


# ---------------------------------------------------------------------------
# internal helper
# ---------------------------------------------------------------------------

def _reset_state():
    audit._entries.clear()  # type: ignore[attr-defined]
