"""Tests for signalhandler.py."""

import signal
import threading
import pytest
import signalhandler


@pytest.fixture(autouse=True)
def _reset():
    signalhandler.reset()
    yield
    signalhandler.reset()


# ---------------------------------------------------------------------------
# is_shutdown / wait
# ---------------------------------------------------------------------------

def test_not_shutdown_initially():
    assert signalhandler.is_shutdown() is False


def test_wait_returns_false_on_timeout():
    result = signalhandler.wait(timeout=0.05)
    assert result is False


def test_wait_returns_true_after_signal():
    # Trigger shutdown via the internal handle directly.
    signalhandler._handle(signal.SIGTERM, None)
    result = signalhandler.wait(timeout=0.1)
    assert result is True


def test_is_shutdown_true_after_handle():
    signalhandler._handle(signal.SIGTERM, None)
    assert signalhandler.is_shutdown() is True


# ---------------------------------------------------------------------------
# hooks
# ---------------------------------------------------------------------------

def test_register_hook_called_on_shutdown():
    called = []
    signalhandler.register_hook(lambda: called.append(True))
    signalhandler._handle(signal.SIGTERM, None)
    assert called == [True]


def test_multiple_hooks_all_called():
    results = []
    signalhandler.register_hook(lambda: results.append(1))
    signalhandler.register_hook(lambda: results.append(2))
    signalhandler._handle(signal.SIGTERM, None)
    assert results == [1, 2]


def test_hook_exception_does_not_prevent_others():
    results = []

    def bad():
        raise RuntimeError("boom")

    signalhandler.register_hook(bad)
    signalhandler.register_hook(lambda: results.append("ok"))
    signalhandler._handle(signal.SIGTERM, None)
    assert results == ["ok"]


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

def test_install_registers_sigterm_and_sigint():
    signalhandler.install()
    assert signal.getsignal(signal.SIGTERM) is signalhandler._handle
    assert signal.getsignal(signal.SIGINT) is signalhandler._handle


def test_install_custom_signal():
    signalhandler.install(signals=[signal.SIGUSR1])
    assert signal.getsignal(signal.SIGUSR1) is signalhandler._handle


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

def test_reset_clears_shutdown_flag():
    signalhandler._handle(signal.SIGTERM, None)
    assert signalhandler.is_shutdown() is True
    signalhandler.reset()
    assert signalhandler.is_shutdown() is False


def test_reset_clears_hooks():
    results = []
    signalhandler.register_hook(lambda: results.append(1))
    signalhandler.reset()
    signalhandler._handle(signal.SIGTERM, None)
    assert results == []


# ---------------------------------------------------------------------------
# thread-safety smoke test
# ---------------------------------------------------------------------------

def test_wait_unblocked_from_another_thread():
    barrier = threading.Barrier(2)
    result_box = []

    def waiter():
        barrier.wait()
        result_box.append(signalhandler.wait(timeout=2.0))

    t = threading.Thread(target=waiter, daemon=True)
    t.start()
    barrier.wait()
    signalhandler._handle(signal.SIGTERM, None)
    t.join(timeout=3.0)
    assert result_box == [True]
