"""Unit tests for replay.py."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from replay import ReplayResult, replay_recent, summary


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_entry(event_id: str = "evt-1", ref: str = "refs/heads/main"):
    e = MagicMock()
    e.event_id = event_id
    e.ref = ref
    return e


def _make_run(returncode: int = 0):
    r = MagicMock()
    r.returncode = returncode
    return r


# ---------------------------------------------------------------------------
# ReplayResult
# ---------------------------------------------------------------------------

def test_replay_result_ok_when_returncode_zero():
    result = ReplayResult(entry=_make_entry(), run=_make_run(0))
    assert result.ok is True


def test_replay_result_not_ok_when_returncode_nonzero():
    result = ReplayResult(entry=_make_entry(), run=_make_run(1))
    assert result.ok is False


def test_replay_result_not_ok_when_skipped():
    result = ReplayResult(entry=_make_entry(), run=None, skipped=True, skip_reason="dry_run")
    assert result.ok is False


# ---------------------------------------------------------------------------
# replay_recent — dry_run
# ---------------------------------------------------------------------------

@patch("replay.recent")
def test_dry_run_skips_execution(mock_recent):
    mock_recent.return_value = [_make_entry("e1"), _make_entry("e2")]
    with patch("replay.run_script") as mock_run:
        results = replay_recent("deploy.sh", limit=2, dry_run=True)
        mock_run.assert_not_called()

    assert len(results) == 2
    assert all(r.skipped for r in results)
    assert all(r.skip_reason == "dry_run" for r in results)


@patch("replay.recent")
def test_dry_run_returns_correct_count(mock_recent):
    mock_recent.return_value = [_make_entry(str(i)) for i in range(4)]
    results = replay_recent("deploy.sh", limit=4, dry_run=True)
    assert len(results) == 4


# ---------------------------------------------------------------------------
# replay_recent — live run
# ---------------------------------------------------------------------------

@patch("replay.recent")
@patch("replay.run_script")
def test_live_run_calls_script_per_entry(mock_run, mock_recent):
    entries = [_make_entry("e1"), _make_entry("e2")]
    mock_recent.return_value = entries
    mock_run.return_value = _make_run(0)

    results = replay_recent("deploy.sh", limit=2)

    assert mock_run.call_count == 2
    assert all(r.ok for r in results)


@patch("replay.recent")
@patch("replay.run_script")
def test_live_run_passes_env_vars(mock_run, mock_recent):
    entry = _make_entry("evt-99", ref="refs/heads/feature")
    mock_recent.return_value = [entry]
    mock_run.return_value = _make_run(0)

    replay_recent("deploy.sh", limit=1)

    _, kwargs = mock_run.call_args
    env = kwargs.get("env", {})
    assert env["REPLAY_EVENT_ID"] == "evt-99"
    assert env["REPLAY_REF"] == "refs/heads/feature"


@patch("replay.recent")
@patch("replay.run_script")
def test_failed_script_not_ok(mock_run, mock_recent):
    mock_recent.return_value = [_make_entry()]
    mock_run.return_value = _make_run(1)

    results = replay_recent("deploy.sh", limit=1)
    assert results[0].ok is False


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

def test_summary_all_ok():
    results = [ReplayResult(entry=_make_entry(), run=_make_run(0)) for _ in range(3)]
    assert summary(results) == "replayed 3: 3 ok, 0 failed, 0 skipped"


def test_summary_mixed():
    results = [
        ReplayResult(entry=_make_entry(), run=_make_run(0)),
        ReplayResult(entry=_make_entry(), run=_make_run(1)),
        ReplayResult(entry=_make_entry(), run=None, skipped=True, skip_reason="dry_run"),
    ]
    assert summary(results) == "replayed 3: 1 ok, 1 failed, 1 skipped"
