"""Tests for metrics.py."""

import time

import pytest

import metrics


@pytest.fixture(autouse=True)
def _reset():
    metrics.reset()
    yield
    metrics.reset()


# ---------------------------------------------------------------------------
# increment / get
# ---------------------------------------------------------------------------

def test_increment_known_counter():
    metrics.increment("deploy.success")
    assert metrics.get("deploy.success") == 1


def test_increment_multiple_times():
    metrics.increment("deploy.failure")
    metrics.increment("deploy.failure")
    metrics.increment("deploy.failure")
    assert metrics.get("deploy.failure") == 3


def test_increment_by_custom_amount():
    metrics.increment("webhook.received", 5)
    assert metrics.get("webhook.received") == 5


def test_increment_unknown_counter_creates_it():
    metrics.increment("custom.event")
    assert metrics.get("custom.event") == 1


def test_get_unknown_counter_returns_zero():
    assert metrics.get("does.not.exist") == 0


def test_reset_zeros_all_counters():
    metrics.increment("deploy.success", 10)
    metrics.increment("deploy.failure", 7)
    metrics.reset()
    assert metrics.get("deploy.success") == 0
    assert metrics.get("deploy.failure") == 0


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------

def test_snapshot_contains_all_default_counters():
    snap = metrics.snapshot()
    for key in (
        "webhook.received",
        "webhook.verified",
        "webhook.rejected",
        "deploy.success",
        "deploy.failure",
    ):
        assert key in snap.counters


def test_snapshot_reflects_increments():
    metrics.increment("deploy.success", 3)
    snap = metrics.snapshot()
    assert snap.counters["deploy.success"] == 3


def test_snapshot_is_isolated_from_later_changes():
    snap = metrics.snapshot()
    metrics.increment("deploy.success", 99)
    assert snap.counters["deploy.success"] == 0


def test_snapshot_uptime_is_positive():
    snap = metrics.snapshot()
    assert snap.uptime_seconds > 0


def test_snapshot_to_dict_has_expected_keys():
    d = metrics.snapshot().to_dict()
    assert "uptime_seconds" in d
    assert "captured_at" in d
    assert "counters" in d


def test_snapshot_uptime_increases():
    snap1 = metrics.snapshot()
    time.sleep(0.05)
    snap2 = metrics.snapshot()
    assert snap2.uptime_seconds > snap1.uptime_seconds


# ---------------------------------------------------------------------------
# thread safety (smoke test)
# ---------------------------------------------------------------------------

def test_concurrent_increments_are_consistent():
    import threading

    def worker():
        for _ in range(100):
            metrics.increment("webhook.received")

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert metrics.get("webhook.received") == 1000
