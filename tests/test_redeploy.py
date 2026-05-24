"""Unit tests for redeploy.py."""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

import audit
from redeploy import RedeployResult, redeploy, _find_entry
from runner import RunResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset():
    audit._entries.clear()


def _entry(ref: str, success: bool = True) -> audit.AuditEntry:
    e = audit.AuditEntry(
        ref=ref,
        script="deploy.sh",
        success=success,
        timestamp=datetime.datetime.utcnow().isoformat(),
        duration=1.0,
        stdout="ok",
        stderr="",
        returncode=0 if success else 1,
    )
    audit._entries.appendleft(e)
    return e


def _run(returncode: int = 0) -> RunResult:
    return RunResult(
        returncode=returncode,
        stdout="out",
        stderr="err",
        duration=0.5,
    )


# ---------------------------------------------------------------------------
# _find_entry
# ---------------------------------------------------------------------------

def test_find_entry_returns_none_when_no_entries():
    _reset()
    assert _find_entry("refs/heads/main") is None


def test_find_entry_returns_matching_ref():
    _reset()
    e = _entry("refs/heads/main")
    assert _find_entry("refs/heads/main") is e


def test_find_entry_ignores_other_refs():
    _reset()
    _entry("refs/heads/other")
    assert _find_entry("refs/heads/main") is None


# ---------------------------------------------------------------------------
# RedeployResult
# ---------------------------------------------------------------------------

def test_redeploy_result_ok_when_returncode_zero():
    r = RedeployResult(ref="refs/heads/main", run=_run(0))
    assert r.ok is True


def test_redeploy_result_not_ok_when_returncode_nonzero():
    r = RedeployResult(ref="refs/heads/main", run=_run(1))
    assert r.ok is False


def test_redeploy_result_not_ok_when_skipped():
    r = RedeployResult(ref="refs/heads/main", run=None, skipped=True, skip_reason="test")
    assert r.ok is False


def test_summary_skipped():
    r = RedeployResult(ref="refs/heads/main", run=None, skipped=True, skip_reason="no prior")
    assert "skipped" in r.summary()
    assert "no prior" in r.summary()


def test_summary_success():
    r = RedeployResult(ref="refs/heads/main", run=_run(0))
    assert "succeeded" in r.summary()


def test_summary_failure():
    r = RedeployResult(ref="refs/heads/main", run=_run(2))
    assert "failed" in r.summary()
    assert "2" in r.summary()


# ---------------------------------------------------------------------------
# redeploy()
# ---------------------------------------------------------------------------

def test_redeploy_skips_when_no_prior_entry():
    _reset()
    result = redeploy("refs/heads/main", script="deploy.sh")
    assert result.skipped is True
    assert result.ok is False


def test_redeploy_runs_script_when_entry_exists():
    _reset()
    _entry("refs/heads/main")
    fake_run = _run(0)
    with patch("redeploy.run_script", return_value=fake_run) as mock_run:
        result = redeploy("refs/heads/main", script="deploy.sh", timeout=30)
    mock_run.assert_called_once_with("deploy.sh", ref="refs/heads/main", timeout=30)
    assert result.ok is True
    assert result.skipped is False


def test_redeploy_returns_failure_on_bad_exit():
    _reset()
    _entry("refs/heads/main")
    with patch("redeploy.run_script", return_value=_run(1)):
        result = redeploy("refs/heads/main", script="deploy.sh")
    assert result.ok is False
