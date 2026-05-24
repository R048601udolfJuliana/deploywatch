"""Audit log: records every webhook delivery and its outcome."""

import json
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional

_lock = threading.Lock()
_entries: List[dict] = []
_MAX_ENTRIES = 200


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AuditEntry:
    event: str
    repository: str
    ref: str
    delivered_at: str = field(default_factory=_utcnow)
    script_exit_code: Optional[int] = None
    notified: Optional[bool] = None
    client_ip: str = "unknown"
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


def record(entry: AuditEntry) -> None:
    """Append *entry* to the in-memory audit log (capped at _MAX_ENTRIES)."""
    with _lock:
        _entries.append(entry.to_dict())
        if len(_entries) > _MAX_ENTRIES:
            del _entries[: len(_entries) - _MAX_ENTRIES]


def recent(limit: int = 20) -> List[dict]:
    """Return up to *limit* most-recent entries (newest first)."""
    with _lock:
        return list(reversed(_entries[-limit:]))


def clear() -> None:
    """Remove all entries — primarily for use in tests."""
    with _lock:
        _entries.clear()


def as_json(limit: int = 20) -> str:
    return json.dumps(recent(limit), indent=2)
