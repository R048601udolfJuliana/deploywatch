"""ratelimit_audit.py – records rate-limit violation events into the audit log."""
from __future__ import annotations

import datetime
from typing import Optional

from audit import record, AuditEntry

# Sentinel ref used for all rate-limit events
_RL_REF = "__rate_limit__"


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


def record_violation(client_ip: str, path: str = "/webhook") -> AuditEntry:
    """Write a rate-limit violation into the audit log and return the entry."""
    entry = record(
        ref=_RL_REF,
        event="rate_limit_violation",
        success=False,
        detail={
            "client_ip": client_ip,
            "path": path,
        },
    )
    return entry


def violation_count(
    since: Optional[datetime.datetime] = None,
    limit: int = 500,
) -> int:
    """Return the number of rate-limit violations recorded since *since*.

    If *since* is None the count covers all stored entries (up to *limit*).
    """
    from audit import recent  # local import to avoid circular dependency

    entries = recent(limit)
    count = 0
    for e in entries:
        if e.event != "rate_limit_violation":
            continue
        if since is not None and e.timestamp < since:
            continue
        count += 1
    return count


def last_violation() -> Optional[AuditEntry]:
    """Return the most recent rate-limit violation entry, or None."""
    from audit import recent

    for e in recent(500):
        if e.event == "rate_limit_violation":
            return e
    return None
