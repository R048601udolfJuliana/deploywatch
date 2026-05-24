"""Unit tests for lockout.py."""

import time
import pytest

from lockout import DeployLockout, LockoutError


@pytest.fixture()
def lo() -> DeployLockout:
    """Lockout with a low threshold for easy testing."""
    return DeployLockout(threshold=3, window=60.0, duration=120.0)


# ---------------------------------------------------------------------------
# check / is_locked
# ---------------------------------------------------------------------------

def test_check_passes_for_unknown_ref(lo: DeployLockout) -> None:
    lo.check("refs/heads/main")  # must not raise


def test_is_locked_false_initially(lo: DeployLockout) -> None:
    assert lo.is_locked("refs/heads/main") is False


# ---------------------------------------------------------------------------
# record_failure → lockout
# ---------------------------------------------------------------------------

def test_below_threshold_does_not_lock(lo: DeployLockout) -> None:
    lo.record_failure("main")
    lo.record_failure("main")
    assert lo.is_locked("main") is False


def test_reaching_threshold_locks(lo: DeployLockout) -> None:
    for _ in range(3):
        lo.record_failure("main")
    assert lo.is_locked("main") is True


def test_check_raises_lockout_error_when_locked(lo: DeployLockout) -> None:
    for _ in range(3):
        lo.record_failure("main")
    with pytest.raises(LockoutError) as exc_info:
        lo.check("main")
    assert exc_info.value.ref == "main"
    assert exc_info.value.unlocks_in > 0


def test_lockout_error_message_contains_ref(lo: DeployLockout) -> None:
    for _ in range(3):
        lo.record_failure("deploy/prod")
    with pytest.raises(LockoutError) as exc_info:
        lo.check("deploy/prod")
    assert "deploy/prod" in str(exc_info.value)


# ---------------------------------------------------------------------------
# record_success clears state
# ---------------------------------------------------------------------------

def test_success_clears_failures(lo: DeployLockout) -> None:
    lo.record_failure("main")
    lo.record_failure("main")
    lo.record_success("main")
    # one more failure should not trigger lockout (counter reset)
    lo.record_failure("main")
    assert lo.is_locked("main") is False


def test_success_on_locked_ref_clears_lockout(lo: DeployLockout) -> None:
    for _ in range(3):
        lo.record_failure("main")
    assert lo.is_locked("main") is True
    lo.record_success("main")
    assert lo.is_locked("main") is False


# ---------------------------------------------------------------------------
# window expiry resets counter
# ---------------------------------------------------------------------------

def test_window_expiry_resets_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    lo = DeployLockout(threshold=3, window=1.0, duration=120.0)
    lo.record_failure("main")
    lo.record_failure("main")
    # advance monotonic clock past the window
    _real = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: _real() + 2.0)
    lo.record_failure("main")   # first failure in new window
    assert lo.is_locked("main") is False


# ---------------------------------------------------------------------------
# lockout expiry releases ref
# ---------------------------------------------------------------------------

def test_lockout_expiry_releases_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    lo = DeployLockout(threshold=2, window=60.0, duration=5.0)
    lo.record_failure("main")
    lo.record_failure("main")
    assert lo.is_locked("main") is True
    _real = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: _real() + 10.0)
    assert lo.is_locked("main") is False


# ---------------------------------------------------------------------------
# status dict
# ---------------------------------------------------------------------------

def test_status_contains_expected_keys(lo: DeployLockout) -> None:
    s = lo.status("main")
    assert {"ref", "failures", "locked", "unlocks_in"} <= s.keys()


def test_status_reflects_locked_state(lo: DeployLockout) -> None:
    for _ in range(3):
        lo.record_failure("main")
    s = lo.status("main")
    assert s["locked"] is True
    assert s["unlocks_in"] > 0
    assert s["failures"] == 3
