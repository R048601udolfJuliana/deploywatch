"""Tests for scheduler.py"""

import threading
import time
import pytest

from scheduler import DigestScheduler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fast_scheduler(callback, interval=0.05):
    """Return a scheduler with a very short interval for testing."""
    return DigestScheduler(callback=callback, interval=interval)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_invalid_interval_raises():
    with pytest.raises(ValueError):
        DigestScheduler(callback=lambda: None, interval=0)


def test_negative_interval_raises():
    with pytest.raises(ValueError):
        DigestScheduler(callback=lambda: None, interval=-10)


def test_not_running_before_start():
    s = DigestScheduler(callback=lambda: None, interval=60)
    assert not s.running


# ---------------------------------------------------------------------------
# Start / stop lifecycle
# ---------------------------------------------------------------------------

def test_running_after_start():
    s = _fast_scheduler(lambda: None)
    s.start()
    try:
        assert s.running
    finally:
        s.stop()


def test_not_running_after_stop():
    s = _fast_scheduler(lambda: None)
    s.start()
    s.stop()
    assert not s.running


def test_start_twice_does_not_create_second_thread():
    s = _fast_scheduler(lambda: None)
    s.start()
    thread_id = s._thread.ident
    s.start()  # second call should be a no-op
    assert s._thread.ident == thread_id
    s.stop()


def test_stop_without_start_is_safe():
    s = DigestScheduler(callback=lambda: None, interval=60)
    s.stop()  # should not raise


# ---------------------------------------------------------------------------
# Callback invocation
# ---------------------------------------------------------------------------

def test_callback_is_called():
    called = threading.Event()
    s = _fast_scheduler(callback=called.set, interval=0.05)
    s.start()
    assert called.wait(timeout=2), "callback was never invoked"
    s.stop()


def test_callback_called_multiple_times():
    counter = {"n": 0}
    lock = threading.Lock()

    def bump():
        with lock:
            counter["n"] += 1

    s = _fast_scheduler(callback=bump, interval=0.05)
    s.start()
    time.sleep(0.25)
    s.stop()
    assert counter["n"] >= 2


def test_exception_in_callback_does_not_stop_scheduler():
    """A crashing callback must not kill the scheduler thread."""
    good_calls = {"n": 0}
    call_count = {"n": 0}

    def flaky():
        call_count["n"] += 1
        if call_count["n"] % 2 == 1:
            raise RuntimeError("boom")
        good_calls["n"] += 1

    s = _fast_scheduler(callback=flaky, interval=0.05)
    s.start()
    time.sleep(0.35)
    s.stop()
    assert s.running is False
    assert good_calls["n"] >= 1
