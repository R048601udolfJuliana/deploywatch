"""Lightweight in-process metrics counters for deploywatch."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict

_lock = threading.Lock()
_started_at: float = time.time()

_counters: Dict[str, int] = {
    "webhook.received": 0,
    "webhook.verified": 0,
    "webhook.rejected": 0,
    "deploy.success": 0,
    "deploy.failure": 0,
    "replay.triggered": 0,
    "rollback.triggered": 0,
    "rate_limit.hit": 0,
    "lockout.triggered": 0,
}


@dataclass
class Snapshot:
    """Immutable point-in-time view of all counters."""

    counters: Dict[str, int]
    uptime_seconds: float
    captured_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "uptime_seconds": round(self.uptime_seconds, 2),
            "captured_at": self.captured_at,
            "counters": dict(self.counters),
        }


def increment(name: str, amount: int = 1) -> None:
    """Increment a named counter by *amount* (default 1).

    Unknown counter names are created on the fly so callers never raise.
    """
    with _lock:
        _counters[name] = _counters.get(name, 0) + amount


def get(name: str) -> int:
    """Return the current value of *name* (0 if unknown)."""
    with _lock:
        return _counters.get(name, 0)


def snapshot() -> Snapshot:
    """Return a consistent copy of all counters plus uptime."""
    with _lock:
        return Snapshot(
            counters=dict(_counters),
            uptime_seconds=time.time() - _started_at,
        )


def reset() -> None:
    """Zero every counter (intended for tests only)."""
    with _lock:
        for key in list(_counters):
            _counters[key] = 0
