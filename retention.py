"""Audit log retention: prune entries older than a configurable window."""

from __future__ import annotations

import datetime
from typing import Optional

import audit


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


def prune(
    max_age_seconds: int = 86_400,
    *,
    _now: Optional[datetime.datetime] = None,
) -> int:
    """Remove audit entries older than *max_age_seconds*.

    Returns the number of entries that were pruned.
    """
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be a positive integer")

    now = _now if _now is not None else _utcnow()
    cutoff = now - datetime.timedelta(seconds=max_age_seconds)

    before = len(audit._LOG)  # noqa: SLF001  (internal access for pruning)
    audit._LOG = [
        entry for entry in audit._LOG
        if entry.timestamp >= cutoff
    ]  # noqa: SLF001
    after = len(audit._LOG)  # noqa: SLF001

    return before - after


def oldest_timestamp() -> Optional[datetime.datetime]:
    """Return the timestamp of the oldest audit entry, or None if empty."""
    if not audit._LOG:  # noqa: SLF001
        return None
    return min(entry.timestamp for entry in audit._LOG)  # noqa: SLF001


def stats(max_age_seconds: int = 86_400) -> dict:
    """Return a summary dict describing current retention state."""
    now = _utcnow()
    cutoff = now - datetime.timedelta(seconds=max_age_seconds)
    total = len(audit._LOG)  # noqa: SLF001
    eligible = sum(
        1 for e in audit._LOG if e.timestamp < cutoff  # noqa: SLF001
    )
    return {
        "total_entries": total,
        "eligible_for_pruning": eligible,
        "max_age_seconds": max_age_seconds,
        "cutoff_utc": cutoff.isoformat() + "Z",
    }
