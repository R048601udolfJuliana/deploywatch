"""Lockout — temporarily block a ref after repeated deployment failures."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

_DEFAULT_THRESHOLD = 3          # failures before lockout
_DEFAULT_WINDOW    = 300.0      # seconds: failure counting window
_DEFAULT_DURATION  = 600.0      # seconds: how long the lockout lasts


@dataclass
class _RefState:
    failures: int = 0
    window_start: float = field(default_factory=time.monotonic)
    locked_until: Optional[float] = None


class LockoutError(Exception):
    """Raised when a ref is currently locked out."""

    def __init__(self, ref: str, unlocks_in: float) -> None:
        self.ref = ref
        self.unlocks_in = unlocks_in
        super().__init__(f"{ref!r} is locked out for {unlocks_in:.0f}s more")


class DeployLockout:
    """Track per-ref failure counts and enforce lockout periods."""

    def __init__(
        self,
        threshold: int = _DEFAULT_THRESHOLD,
        window: float = _DEFAULT_WINDOW,
        duration: float = _DEFAULT_DURATION,
    ) -> None:
        self._threshold = threshold
        self._window    = window
        self._duration  = duration
        self._state: Dict[str, _RefState] = {}
        self._lock = threading.Lock()

    def _get(self, ref: str) -> _RefState:
        if ref not in self._state:
            self._state[ref] = _RefState()
        return self._state[ref]

    def check(self, ref: str) -> None:
        """Raise LockoutError if *ref* is currently locked out."""
        with self._lock:
            state = self._get(ref)
            if state.locked_until is not None:
                remaining = state.locked_until - time.monotonic()
                if remaining > 0:
                    raise LockoutError(ref, remaining)
                # lockout expired — reset
                self._state[ref] = _RefState()

    def record_failure(self, ref: str) -> None:
        """Record a deployment failure; lock the ref when threshold is hit."""
        with self._lock:
            state = self._get(ref)
            now = time.monotonic()
            # reset window if it has expired
            if now - state.window_start > self._window:
                state.failures    = 0
                state.window_start = now
            state.failures += 1
            if state.failures >= self._threshold:
                state.locked_until = now + self._duration

    def record_success(self, ref: str) -> None:
        """Clear failure count after a successful deployment."""
        with self._lock:
            self._state.pop(ref, None)

    def is_locked(self, ref: str) -> bool:
        """Return True if *ref* is currently locked out."""
        try:
            self.check(ref)
            return False
        except LockoutError:
            return True

    def status(self, ref: str) -> Dict[str, object]:
        """Return a status dict for *ref* (useful for health/audit endpoints)."""
        with self._lock:
            state = self._get(ref)
            now   = time.monotonic()
            locked = (
                state.locked_until is not None
                and state.locked_until > now
            )
            return {
                "ref":         ref,
                "failures":    state.failures,
                "locked":      locked,
                "unlocks_in":  max(0.0, (state.locked_until or 0) - now),
            }
