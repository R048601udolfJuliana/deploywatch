"""pausecontrol.py — Global deploy pause/resume toggle with reason tracking."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

from logger import get_logger

log = get_logger(__name__)


@dataclass
class PauseState:
    paused: bool = False
    reason: str = ""
    paused_at: Optional[str] = None
    resumed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "paused": self.paused,
            "reason": self.reason,
            "paused_at": self.paused_at,
            "resumed_at": self.resumed_at,
        }


class DeployPaused(Exception):
    """Raised when a deploy is attempted while deploys are paused."""

    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        super().__init__(f"Deploys are paused: {reason}" if reason else "Deploys are paused")


_lock = threading.Lock()
_state = PauseState()


def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def pause(reason: str = "") -> PauseState:
    """Pause all deploys, optionally recording a reason."""
    global _state
    with _lock:
        _state = PauseState(
            paused=True,
            reason=reason,
            paused_at=_utcnow(),
            resumed_at=None,
        )
    log.info("deploys_paused", extra={"reason": reason})
    return _state


def resume() -> PauseState:
    """Resume deploys."""
    global _state
    with _lock:
        _state = PauseState(
            paused=False,
            reason=_state.reason,
            paused_at=_state.paused_at,
            resumed_at=_utcnow(),
        )
    log.info("deploys_resumed")
    return _state


def check() -> None:
    """Raise DeployPaused if deploys are currently paused."""
    with _lock:
        if _state.paused:
            raise DeployPaused(_state.reason)


def status() -> PauseState:
    """Return a copy of the current pause state."""
    with _lock:
        return PauseState(
            paused=_state.paused,
            reason=_state.reason,
            paused_at=_state.paused_at,
            resumed_at=_state.resumed_at,
        )


def reset() -> None:
    """Reset to unpaused state (primarily for tests)."""
    global _state
    with _lock:
        _state = PauseState()
