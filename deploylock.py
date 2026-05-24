"""deploylock.py – global deploy lock (pause all deploys for maintenance).

Distinct from pausecontrol (per-ref) – this is a binary global gate.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional


class DeployLockError(Exception):
    """Raised when a deploy is attempted while the global lock is active."""


_lock = threading.Lock()
_locked: bool = False
_locked_by: str = ""
_locked_at: Optional[datetime] = None
_reason: str = ""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def acquire(operator: str, reason: str = "") -> None:
    """Engage the global deploy lock."""
    global _locked, _locked_by, _locked_at, _reason
    with _lock:
        _locked = True
        _locked_by = operator
        _locked_at = _utcnow()
        _reason = reason


def release() -> None:
    """Disengage the global deploy lock."""
    global _locked, _locked_by, _locked_at, _reason
    with _lock:
        _locked = False
        _locked_by = ""
        _locked_at = None
        _reason = ""


def check() -> None:
    """Raise DeployLockError if the global lock is active."""
    with _lock:
        if _locked:
            msg = f"Global deploy lock active (operator={_locked_by!r}, reason={_reason!r})"
            raise DeployLockError(msg)


def status() -> dict:
    """Return a dict describing the current lock state."""
    with _lock:
        return {
            "locked": _locked,
            "locked_by": _locked_by,
            "locked_at": _locked_at.isoformat() if _locked_at else None,
            "reason": _reason,
        }


def _reset() -> None:
    """Reset module state (test helper)."""
    release()
