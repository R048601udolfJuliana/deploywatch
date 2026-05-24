"""Unit tests for rollback.py."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

import audit
from audit import AuditEntry
from rollback import RollbackResult, rollback, _last_success
from runner import RunResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _reset():
    audit._entries.clear()


def _ts(offset: int = 0) -> datetime.datetime:
    return datetime.datetime(2024, 1, 1, 12, 0, 0) + datetime.timedelta(seconds=offset)


def _entry(ref="refs/heads/main", sha="abc123", success=True, offset=0) -> AuditEntry:
    e = AuditEntry(
        timestamp=_ts(offset),
        ref=ref,
        sha=sha,
        success=success,
        returncode=0 if success else 1,
        duration=1.0,
    )
    audit._entries.append(e)
    return e


_GOOD_RUN = RunResult(returncode=0, stdout="ok", stderr="", duration=0.5)
_BAD_RUN = RunResult(returncode=1, stdout="", stderr="err", duration=0.5)


# ---------------------------------------------------------------------------
# _last_success
# ---------------------------------------------------------------------------

def test_last_success_returns_none_when_no_entries():
    _reset()
    assert _last_success("refs/heads/main") is None


def test_last_success_ignores_failures():
    _reset()
    _entry(success=False, offset=0)
    assert _last_success("refs/heads/main") is None


def test_last_success_returns_most_recent():
    _reset()
    e1 = _entry(sha="old", success=True, offset=0)
    e2 = _entry(sha="new", success=True, offset=10)
    # recent() returns newest first, so e2 should win
    result = _last_success("refs/heads/main")
    assert result is not None
    assert result.sha == "new"


def test_last_success_filters_by_ref():
    _reset()
    _entry(ref="refs/heads/other", success=True)
    assert _last_success("refs/heads/main") is None


# ---------------------------------------------------------------------------
# RollbackResult
# ---------------------------------------------------------------------------

def test_rollback_result_ok_when_returncode_zero():
    r = RollbackResult(ref="refs/heads/main", entry=MagicMock(), run=_GOOD_RUN)
    assert r.ok is True


def test_rollback_result_not_ok_when_returncode_nonzero():
    r = RollbackResult(ref="refs/heads/main", entry=MagicMock(), run=_BAD_RUN)
    assert r.ok is False


def test_rollback_result_not_ok_when_skipped():
    r = RollbackResult(ref="refs/heads/main", entry=None, run=None,
                       skipped=True, skip_reason="no history")
    assert r.ok is False
    assert "skipped" in r.summary()


def test_rollback_result_summary_success():
    r = RollbackResult(ref="refs/heads/main", entry=MagicMock(), run=_GOOD_RUN)
    assert "succeeded" in r.summary()


def test_rollback_result_summary_failure():
    r = RollbackResult(ref="refs/heads/main", entry=MagicMock(), run=_BAD_RUN)
    assert "failed" in r.summary()


# ---------------------------------------------------------------------------
# rollback()
# ---------------------------------------------------------------------------

def test_rollback_skips_when_no_history():
    _reset()
    result = rollback("refs/heads/main", "/deploy.sh")
    assert result.skipped is True
    assert result.ok is False


def test_rollback_calls_run_script_with_last_good_entry():
    _reset()
    e = _entry(sha="deadbeef", success=True)
    with patch("rollback.run_script", return_value=_GOOD_RUN) as mock_run:
        result = rollback("refs/heads/main", "/deploy.sh", timeout=30)
    mock_run.assert_called_once_with("/deploy.sh", ref=e.ref, sha=e.sha, timeout=30)
    assert result.ok is True
    assert result.entry is e


def test_rollback_propagates_script_failure():
    _reset()
    _entry(sha="deadbeef", success=True)
    with patch("rollback.run_script", return_value=_BAD_RUN):
        result = rollback("refs/heads/main", "/deploy.sh")
    assert result.ok is False
    assert result.skipped is False
