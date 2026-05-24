"""Graceful shutdown signal handler for deploywatch."""

import signal
import logging
import threading
from typing import Callable, List, Optional

log = logging.getLogger(__name__)

_shutdown_event: threading.Event = threading.Event()
_hooks: List[Callable[[], None]] = []


def register_hook(fn: Callable[[], None]) -> None:
    """Register a callable to be invoked on shutdown signal."""
    _hooks.append(fn)


def is_shutdown() -> bool:
    """Return True if a shutdown signal has been received."""
    return _shutdown_event.is_set()


def wait(timeout: Optional[float] = None) -> bool:
    """Block until shutdown is signalled or timeout expires.

    Returns True if shutdown was signalled, False on timeout.
    """
    return _shutdown_event.wait(timeout=timeout)


def _handle(signum: int, _frame) -> None:  # type: ignore[type-arg]
    sig_name = signal.Signals(signum).name
    log.info("received signal %s — initiating graceful shutdown", sig_name)
    _shutdown_event.set()
    for hook in _hooks:
        try:
            hook()
        except Exception:
            log.exception("error in shutdown hook %r", hook)


def install(signals: Optional[List[signal.Signals]] = None) -> None:
    """Install signal handlers for graceful shutdown.

    Defaults to SIGTERM and SIGINT if *signals* is not provided.
    Must be called from the main thread.
    """
    if signals is None:
        signals = [signal.SIGTERM, signal.SIGINT]
    for sig in signals:
        signal.signal(sig, _handle)
        log.debug("installed handler for %s", sig.name)


def reset() -> None:
    """Reset internal state (intended for tests only)."""
    _shutdown_event.clear()
    _hooks.clear()
