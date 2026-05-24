"""Tests for pausecontrol.py"""

import pytest

import pausecontrol
from pausecontrol import (
    DeployPaused,
    check,
    pause,
    reset,
    resume,
    status,
)


@pytest.fixture(autouse=True)
def _reset():
    reset()
    yield
    reset()


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

def test_not_paused_initially():
    assert status().paused is False


def test_reason_empty_initially():
    assert status().reason == ""


def test_check_passes_when_not_paused():
    check()  # should not raise


# ---------------------------------------------------------------------------
# pause()
# ---------------------------------------------------------------------------

def test_pause_sets_paused_true():
    pause()
    assert status().paused is True


def test_pause_stores_reason():
    pause(reason="maintenance window")
    assert status().reason == "maintenance window"


def test_pause_records_paused_at():
    pause()
    assert status().paused_at is not None


def test_pause_clears_resumed_at():
    resume()
    pause()
    assert status().resumed_at is None


def test_pause_returns_state():
    state = pause(reason="test")
    assert state.paused is True
    assert state.reason == "test"


# ---------------------------------------------------------------------------
# check() raises when paused
# ---------------------------------------------------------------------------

def test_check_raises_when_paused():
    pause(reason="blocked")
    with pytest.raises(DeployPaused):
        check()


def test_deploy_paused_carries_reason():
    pause(reason="rollback in progress")
    with pytest.raises(DeployPaused) as exc_info:
        check()
    assert "rollback in progress" in str(exc_info.value)


def test_deploy_paused_no_reason_still_raises():
    pause()
    with pytest.raises(DeployPaused):
        check()


# ---------------------------------------------------------------------------
# resume()
# ---------------------------------------------------------------------------

def test_resume_clears_paused_flag():
    pause()
    resume()
    assert status().paused is False


def test_resume_records_resumed_at():
    pause()
    resume()
    assert status().resumed_at is not None


def test_resume_preserves_reason():
    pause(reason="hotfix")
    resume()
    assert status().reason == "hotfix"


def test_check_passes_after_resume():
    pause()
    resume()
    check()  # should not raise


def test_resume_returns_state():
    pause()
    state = resume()
    assert state.paused is False


# ---------------------------------------------------------------------------
# to_dict()
# ---------------------------------------------------------------------------

def test_to_dict_has_required_keys():
    d = status().to_dict()
    assert set(d.keys()) == {"paused", "reason", "paused_at", "resumed_at"}


def test_to_dict_paused_true_after_pause():
    pause(reason="x")
    d = status().to_dict()
    assert d["paused"] is True
    assert d["reason"] == "x"


def test_to_dict_is_json_serialisable():
    import json
    pause(reason="json test")
    resume()
    json.dumps(status().to_dict())  # must not raise
