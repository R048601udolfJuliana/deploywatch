"""drain.py — Graceful shutdown helper that waits for in-flight deploys to finish."""

from __future__ import annotations

import threading
import time
from typing import Optional

from logger import get_logger

log = get_logger(__name__)

_DEFAULT_TIMEOUT = 30  # seconds


class DrainTimeout(Exception):
    """Raised when drain() exceeds the allowed timeout."""


class DeployDrain:
    """Tracks in-flight deploys and blocks shutdown until they complete."""

    def __init__(self, timeout: int = _DEFAULT_TIMEOUT) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be a positive integer")
        self._timeout = timeout
        self._lock = threading.Lock()
        self._count = 0
        self._idle = threading.Event()
        self._idle.set()  # starts idle
        self._draining = False

    # ------------------------------------------------------------------
    # Context-manager interface
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Register a new in-flight deploy. Raises RuntimeError if draining."""
        with self._lock:
            if self._draining:
                raise RuntimeError("Server is draining; no new deploys accepted")
            self._count += 1
            self._idle.clear()
            log.debug("drain: acquired", extra={"in_flight": self._count})

    def release(self) -> None:
        """Mark one in-flight deploy as finished."""
        with self._lock:
            self._count = max(0, self._count - 1)
            log.debug("drain: released", extra={"in_flight": self._count})
            if self._count == 0:
                self._idle.set()

    def __enter__(self) -> "DeployDrain":
        self.acquire()
        return self

    def __exit__(self, *_) -> None:
        self.release()

    # ------------------------------------------------------------------
    # Drain / status
    # ------------------------------------------------------------------

    def drain(self, timeout: Optional[int] = None) -> None:
        """Block until all in-flight deploys finish or *timeout* seconds elapse."""
        wait = timeout if timeout is not None else self._timeout
        with self._lock:
            self._draining = True
            remaining = self._count
        log.info("drain: waiting for in-flight deploys", extra={"in_flight": remaining})
        if not self._idle.wait(timeout=wait):
            raise DrainTimeout(
                f"drain timed out after {wait}s with {self._count} deploy(s) still running"
            )
        log.info("drain: all deploys finished")

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._count

    @property
    def is_draining(self) -> bool:
        with self._lock:
            return self._draining
