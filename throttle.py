"""Deployment throttle: prevents the same ref from being deployed concurrently."""

import threading
import time
from typing import Dict, Optional


class ThrottleError(Exception):
    """Raised when a deployment is already in progress for a ref."""


class DeployThrottle:
    """Tracks in-progress deployments by ref and enforces a cooldown period."""

    def __init__(self, cooldown_seconds: float = 30.0) -> None:
        self._cooldown = cooldown_seconds
        self._lock = threading.Lock()
        # ref -> timestamp when the lock was acquired
        self._active: Dict[str, float] = {}

    def acquire(self, ref: str) -> None:
        """Mark *ref* as deploying.  Raises ThrottleError if already active."""
        with self._lock:
            now = time.monotonic()
            started = self._active.get(ref)
            if started is not None:
                elapsed = now - started
                if elapsed < self._cooldown:
                    remaining = self._cooldown - elapsed
                    raise ThrottleError(
                        f"Deployment for '{ref}' already in progress "
                        f"(cooldown: {remaining:.1f}s remaining)"
                    )
                # Cooldown expired — treat previous run as abandoned
            self._active[ref] = now

    def release(self, ref: str) -> None:
        """Mark *ref* deployment as finished."""
        with self._lock:
            self._active.pop(ref, None)

    def is_active(self, ref: str) -> bool:
        """Return True if *ref* is currently deploying within the cooldown window."""
        with self._lock:
            started = self._active.get(ref)
            if started is None:
                return False
            return (time.monotonic() - started) < self._cooldown

    def active_refs(self) -> Dict[str, float]:
        """Return a snapshot of {ref: elapsed_seconds} for active deployments."""
        with self._lock:
            now = time.monotonic()
            return {
                ref: now - started
                for ref, started in self._active.items()
                if (now - started) < self._cooldown
            }

    # Context-manager helpers for convenience
    def __call__(self, ref: str):
        """Use as: with throttle(ref): ..."""
        return _ThrottleContext(self, ref)


class _ThrottleContext:
    def __init__(self, throttle: DeployThrottle, ref: str) -> None:
        self._throttle = throttle
        self._ref = ref

    def __enter__(self) -> None:
        self._throttle.acquire(self._ref)

    def __exit__(self, *_) -> None:
        self._throttle.release(self._ref)
