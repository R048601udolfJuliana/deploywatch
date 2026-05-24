"""Simple in-memory rate limiter for webhook requests."""

import time
import threading
from collections import defaultdict
from typing import Dict, List


class RateLimiter:
    """Token-bucket style rate limiter keyed by client IP."""

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._buckets: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        """Return True if the request should be allowed, False if rate-limited."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._buckets[client_ip]
            # Evict timestamps outside the current window
            self._buckets[client_ip] = [t for t in timestamps if t > cutoff]
            if len(self._buckets[client_ip]) >= self.max_requests:
                return False
            self._buckets[client_ip].append(now)
            return True

    def remaining(self, client_ip: str) -> int:
        """Return the number of requests still allowed in the current window."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            count = sum(1 for t in self._buckets[client_ip] if t > cutoff)
            return max(0, self.max_requests - count)

    def reset(self, client_ip: str | None = None) -> None:
        """Clear rate-limit state for one IP or all IPs."""
        with self._lock:
            if client_ip is None:
                self._buckets.clear()
            else:
                self._buckets.pop(client_ip, None)
