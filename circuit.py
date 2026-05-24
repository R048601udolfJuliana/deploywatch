"""Circuit breaker for deployment scripts.

Prevents cascading failures by temporarily halting deploys for a ref
after a configurable number of consecutive failures within a time window.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

_OPEN = "open"
_CLOSED = "closed"
_HALF_OPEN = "half_open"


@dataclass
class _BreakerState:
    state: str = _CLOSED
    failures: int = 0
    opened_at: Optional[float] = None


class CircuitOpenError(Exception):
    """Raised when a deploy is attempted while the circuit is open."""

    def __init__(self, ref: str, retry_in: float) -> None:
        self.ref = ref
        self.retry_in = retry_in
        super().__init__(
            f"Circuit open for {ref!r}; retry in {retry_in:.1f}s"
        )


class CircuitBreaker:
    """Per-ref circuit breaker."""

    def __init__(
        self,
        threshold: int = 3,
        recovery_timeout: float = 60.0,
    ) -> None:
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")
        self._threshold = threshold
        self._recovery_timeout = recovery_timeout
        self._states: Dict[str, _BreakerState] = {}
        self._lock = threading.Lock()

    def _state(self, ref: str) -> _BreakerState:
        if ref not in self._states:
            self._states[ref] = _BreakerState()
        return self._states[ref]

    def check(self, ref: str) -> None:
        """Raise CircuitOpenError if deploys for *ref* are currently blocked."""
        with self._lock:
            s = self._state(ref)
            if s.state == _OPEN:
                elapsed = time.monotonic() - (s.opened_at or 0)
                remaining = self._recovery_timeout - elapsed
                if remaining > 0:
                    raise CircuitOpenError(ref, remaining)
                s.state = _HALF_OPEN

    def record_success(self, ref: str) -> None:
        """Record a successful deploy, resetting the breaker for *ref*."""
        with self._lock:
            self._states[ref] = _BreakerState()

    def record_failure(self, ref: str) -> None:
        """Record a failed deploy; open the circuit if threshold is reached."""
        with self._lock:
            s = self._state(ref)
            s.failures += 1
            if s.failures >= self._threshold:
                s.state = _OPEN
                s.opened_at = time.monotonic()

    def status(self, ref: str) -> str:
        """Return the current state string for *ref*."""
        with self._lock:
            return self._state(ref).state

    def reset(self, ref: str) -> None:
        """Manually reset the circuit for *ref* (e.g. operator intervention)."""
        with self._lock:
            self._states.pop(ref, None)
