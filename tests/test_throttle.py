"""Tests for throttle.py"""

import time
import threading
import pytest

from throttle import DeployThrottle, ThrottleError


REF = "refs/heads/main"


@pytest.fixture()
def throttle():
    return DeployThrottle(cooldown_seconds=30.0)


def test_acquire_first_time_succeeds(throttle):
    throttle.acquire(REF)  # should not raise


def test_acquire_same_ref_twice_raises(throttle):
    throttle.acquire(REF)
    with pytest.raises(ThrottleError, match=REF):
        throttle.acquire(REF)


def test_release_allows_reacquire(throttle):
    throttle.acquire(REF)
    throttle.release(REF)
    throttle.acquire(REF)  # should not raise


def test_release_unknown_ref_is_noop(throttle):
    throttle.release("refs/heads/nonexistent")  # must not raise


def test_is_active_true_while_locked(throttle):
    throttle.acquire(REF)
    assert throttle.is_active(REF) is True


def test_is_active_false_after_release(throttle):
    throttle.acquire(REF)
    throttle.release(REF)
    assert throttle.is_active(REF) is False


def test_is_active_false_for_unknown_ref(throttle):
    assert throttle.is_active("refs/heads/other") is False


def test_cooldown_expiry_allows_reacquire(monkeypatch):
    """After cooldown expires an abandoned lock should be overwritten."""
    t = DeployThrottle(cooldown_seconds=1.0)
    t.acquire(REF)
    # Wind time forward past the cooldown
    original = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: original() + 2.0)
    t.acquire(REF)  # should not raise — cooldown has expired


def test_active_refs_returns_elapsed(throttle):
    throttle.acquire(REF)
    snapshot = throttle.active_refs()
    assert REF in snapshot
    assert snapshot[REF] >= 0.0


def test_active_refs_excludes_released(throttle):
    throttle.acquire(REF)
    throttle.release(REF)
    assert REF not in throttle.active_refs()


def test_different_refs_are_independent(throttle):
    ref_a = "refs/heads/main"
    ref_b = "refs/heads/staging"
    throttle.acquire(ref_a)
    throttle.acquire(ref_b)  # different ref — must not raise
    assert throttle.is_active(ref_a)
    assert throttle.is_active(ref_b)


def test_context_manager_acquires_and_releases(throttle):
    with throttle(REF):
        assert throttle.is_active(REF)
    assert not throttle.is_active(REF)


def test_context_manager_releases_on_exception(throttle):
    with pytest.raises(RuntimeError):
        with throttle(REF):
            raise RuntimeError("boom")
    assert not throttle.is_active(REF)


def test_thread_safety():
    """Concurrent acquires for the same ref: exactly one must succeed."""
    t = DeployThrottle(cooldown_seconds=30.0)
    results = []
    barrier = threading.Barrier(10)

    def worker():
        barrier.wait()
        try:
            t.acquire(REF)
            results.append("ok")
        except ThrottleError:
            results.append("blocked")

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert results.count("ok") == 1
    assert results.count("blocked") == 9
