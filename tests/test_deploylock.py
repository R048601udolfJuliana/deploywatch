"""Tests for deploylock.py."""
from __future__ import annotations

import pytest
import deploylock
from deploylock import DeployLockError, acquire, check, release, status, _reset


@pytest.fixture(autouse=True)
def reset():
    _reset()
    yield
    _reset()


def test_not_locked_initially():
    assert status()["locked"] is False


def test_check_passes_when_not_locked():
    check()  # must not raise


def test_acquire_sets_locked_true():
    acquire("alice")
    assert status()["locked"] is True


def test_acquire_stores_operator():
    acquire("bob", reason="maintenance")
    s = status()
    assert s["locked_by"] == "bob"


def test_acquire_stores_reason():
    acquire("alice", reason="db migration")
    assert status()["reason"] == "db migration"


def test_acquire_stores_locked_at_timestamp():
    acquire("alice")
    assert status()["locked_at"] is not None


def test_check_raises_when_locked():
    acquire("ops")
    with pytest.raises(DeployLockError):
        check()


def test_check_error_message_contains_operator():
    acquire("carol", reason="hotfix")
    with pytest.raises(DeployLockError, match="carol"):
        check()


def test_release_clears_lock():
    acquire("alice")
    release()
    assert status()["locked"] is False


def test_release_clears_operator():
    acquire("alice")
    release()
    assert status()["locked_by"] == ""


def test_release_clears_locked_at():
    acquire("alice")
    release()
    assert status()["locked_at"] is None


def test_release_clears_reason():
    acquire("alice", reason="test")
    release()
    assert status()["reason"] == ""


def test_check_passes_after_release():
    acquire("alice")
    release()
    check()  # must not raise


def test_acquire_without_reason_defaults_empty():
    acquire("dave")
    assert status()["reason"] == ""


def test_status_locked_at_is_iso_string():
    acquire("eve")
    locked_at = status()["locked_at"]
    assert isinstance(locked_at, str)
    assert "T" in locked_at  # rough ISO check


def test_double_acquire_overwrites():
    acquire("first", reason="r1")
    acquire("second", reason="r2")
    s = status()
    assert s["locked_by"] == "second"
    assert s["reason"] == "r2"
