"""Integration tests: metrics incremented by other modules at call sites."""

import pytest

import metrics
import audit
import runner


@pytest.fixture(autouse=True)
def _reset_all(tmp_path):
    metrics.reset()
    # reset audit store
    audit._entries.clear()  # type: ignore[attr-defined]
    yield
    metrics.reset()
    audit._entries.clear()  # type: ignore[attr-defined]


@pytest.fixture()
def passing_script(tmp_path):
    p = tmp_path / "pass.sh"
    p.write_text("#!/bin/sh\nexit 0\n")
    p.chmod(0o755)
    return str(p)


@pytest.fixture()
def failing_script(tmp_path):
    p = tmp_path / "fail.sh"
    p.write_text("#!/bin/sh\nexit 1\n")
    p.chmod(0o755)
    return str(p)


def test_snapshot_to_dict_is_json_serialisable():
    import json

    metrics.increment("deploy.success", 2)
    metrics.increment("deploy.failure", 1)
    d = metrics.snapshot().to_dict()
    dumped = json.dumps(d)  # must not raise
    reloaded = json.loads(dumped)
    assert reloaded["counters"]["deploy.success"] == 2
    assert reloaded["counters"]["deploy.failure"] == 1


def test_multiple_snapshots_are_independent():
    metrics.increment("rate_limit.hit", 3)
    snap_a = metrics.snapshot()
    metrics.increment("rate_limit.hit", 2)
    snap_b = metrics.snapshot()

    assert snap_a.counters["rate_limit.hit"] == 3
    assert snap_b.counters["rate_limit.hit"] == 5


def test_uptime_reported_in_seconds():
    """Uptime must be a non-negative float (seconds, not ms)."""
    snap = metrics.snapshot()
    # If uptime were in milliseconds it would be >= 1000 almost immediately;
    # in seconds it should be well under 60 in a test context.
    assert 0 <= snap.uptime_seconds < 60


def test_unknown_event_names_accumulate():
    for name in ("custom.a", "custom.b", "custom.a"):
        metrics.increment(name)
    snap = metrics.snapshot()
    assert snap.counters["custom.a"] == 2
    assert snap.counters["custom.b"] == 1
