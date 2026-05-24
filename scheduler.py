"""Periodic digest scheduler — sends Slack digests on a configurable interval."""

import threading
import time
import logging
from typing import Optional, Callable

log = logging.getLogger(__name__)

_DEFAULT_INTERVAL = 3600  # seconds


class DigestScheduler:
    """Runs a digest callback on a fixed interval in a background thread."""

    def __init__(
        self,
        callback: Callable[[], None],
        interval: int = _DEFAULT_INTERVAL,
    ) -> None:
        if interval <= 0:
            raise ValueError(f"interval must be positive, got {interval}")
        self._callback = callback
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background scheduler thread."""
        if self._thread is not None and self._thread.is_alive():
            log.warning("scheduler already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="digest-scheduler",
            daemon=True,
        )
        self._thread.start()
        log.info("digest scheduler started (interval=%ds)", self._interval)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the scheduler to stop and wait for the thread to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        log.info("digest scheduler stopped")

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        """Sleep in short ticks so stop() is responsive."""
        tick = min(1, self._interval)
        elapsed = 0.0
        while not self._stop_event.is_set():
            time.sleep(tick)
            elapsed += tick
            if elapsed >= self._interval:
                elapsed = 0.0
                try:
                    self._callback()
                except Exception:  # noqa: BLE001
                    log.exception("digest callback raised an exception")
