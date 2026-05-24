"""Tests for retention.py — audit log pruning."""

from __future__ import annotations

import datetime

import pytest

import audit
import retention


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _reset():
    audit._LOG.clear()  # noqa: SLF001


def _ts(seconds_ago: float, *, base: datetime.datetime | None = None) -> datetime.datetime:
    base = base or datetime.datetime.utcnow()
    return base - datetime.timedelta(seconds=seconds_ago)


def _seed(ref: str, ok: bool, seconds_ago: float, base: datetime.datetime) -> None:
    entry = audit.AuditEntry(
        ref=ref,
        script="deploy.sh",
        success=ok,
        returncode=0 if ok else 1,
        duration=1.0,
        timestamp=_ts(seconds_ago, base=base),
    )
    audit._LOG.append(entry)  # noqa: SLF001


# ---------------------------------------------------------------------------
# prune
# ---------------------------------------------------------------------------

def test_prune_removes_old_entries():
    _reset()
    now = datetime.datetime.utcnow()
    _seed("main", True, 7200, now)   # 2 h old  → should be pruned
    _seed("main", True, 100, now)    # 100 s old → kept
    removed = retention.prune(max_age_seconds=3600, _now=now)
    assert removed == 1
    assert len(audit._LOG) == 1  # noqa: SLF001


def test_prune_keeps_recent_entries():
    _reset()
    now = datetime.datetime.utcnow()
    _seed("main", True, 10, now)
    _seed("dev", False, 20, now)
    removed = retention.prune(max_age_seconds=3600, _now=now)
    assert removed == 0
    assert len(audit._LOG) == 2  # noqa: SLF001


def test_prune_empty_log_returns_zero():
    _reset()
    assert retention.prune(max_age_seconds=3600) == 0


def test_prune_removes_all_when_all_old():
    _reset()
    now = datetime.datetime.utcnow()
    for i in range(5):
        _seed(f"ref-{i}", True, 10_000 + i, now)
    removed = retention.prune(max_age_seconds=60, _now=now)
    assert removed == 5
    assert audit._LOG == []  # noqa: SLF001


def test_prune_raises_on_invalid_max_age():
    with pytest.raises(ValueError):
        retention.prune(max_age_seconds=0)
    with pytest.raises(ValueError):
        retention.prune(max_age_seconds=-1)


# ---------------------------------------------------------------------------
# oldest_timestamp
# ---------------------------------------------------------------------------

def test_oldest_timestamp_none_when_empty():
    _reset()
    assert retention.oldest_timestamp() is None


def test_oldest_timestamp_returns_minimum():
    _reset()
    now = datetime.datetime.utcnow()
    _seed("a", True, 500, now)
    _seed("b", True, 100, now)
    _seed("c", True, 900, now)
    oldest = retention.oldest_timestamp()
    assert oldest is not None
    # 900 seconds ago is the oldest
    assert oldest < now - datetime.timedelta(seconds=800)


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

def test_stats_zero_counts_when_empty():
    _reset()
    s = retention.stats(max_age_seconds=3600)
    assert s["total_entries"] == 0
    assert s["eligible_for_pruning"] == 0


def test_stats_counts_eligible_entries():
    _reset()
    now = datetime.datetime.utcnow()
    _seed("main", True, 7200, now)   # old
    _seed("main", True, 10, now)     # recent
    s = retention.stats(max_age_seconds=3600)
    assert s["total_entries"] == 2
    assert s["eligible_for_pruning"] == 1


def test_stats_contains_expected_keys():
    _reset()
    s = retention.stats()
    assert "total_entries" in s
    assert "eligible_for_pruning" in s
    assert "max_age_seconds" in s
    assert "cutoff_utc" in s
