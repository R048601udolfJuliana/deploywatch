"""Tests for ratelimit.py"""

import time
import threading
import pytest
from unittest.mock import patch
from ratelimit import RateLimiter


IP = "127.0.0.1"
OTHER_IP = "10.0.0.1"


def test_first_request_is_allowed():
    rl = RateLimiter(max_requests=5, window_seconds=60)
    assert rl.is_allowed(IP) is True


def test_requests_within_limit_are_allowed():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        assert rl.is_allowed(IP) is True


def test_request_over_limit_is_denied():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        rl.is_allowed(IP)
    assert rl.is_allowed(IP) is False


def test_remaining_decreases_with_each_request():
    rl = RateLimiter(max_requests=5, window_seconds=60)
    assert rl.remaining(IP) == 5
    rl.is_allowed(IP)
    assert rl.remaining(IP) == 4
    rl.is_allowed(IP)
    assert rl.remaining(IP) == 3


def test_remaining_never_goes_negative():
    rl = RateLimiter(max_requests=2, window_seconds=60)
    for _ in range(5):
        rl.is_allowed(IP)
    assert rl.remaining(IP) == 0


def test_window_expiry_allows_new_requests():
    rl = RateLimiter(max_requests=2, window_seconds=1)
    rl.is_allowed(IP)
    rl.is_allowed(IP)
    assert rl.is_allowed(IP) is False
    time.sleep(1.05)
    assert rl.is_allowed(IP) is True


def test_different_ips_are_tracked_independently():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    assert rl.is_allowed(IP) is True
    assert rl.is_allowed(IP) is False
    assert rl.is_allowed(OTHER_IP) is True


def test_reset_single_ip():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    rl.is_allowed(IP)
    assert rl.is_allowed(IP) is False
    rl.reset(IP)
    assert rl.is_allowed(IP) is True


def test_reset_all_ips():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    rl.is_allowed(IP)
    rl.is_allowed(OTHER_IP)
    rl.reset()
    assert rl.is_allowed(IP) is True
    assert rl.is_allowed(OTHER_IP) is True


def test_invalid_max_requests_raises():
    with pytest.raises(ValueError, match="max_requests"):
        RateLimiter(max_requests=0)


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        RateLimiter(window_seconds=0)


def test_thread_safety():
    """Concurrent requests should not exceed the limit."""
    rl = RateLimiter(max_requests=50, window_seconds=60)
    results = []
    lock = threading.Lock()

    def make_request():
        allowed = rl.is_allowed(IP)
        with lock:
            results.append(allowed)

    threads = [threading.Thread(target=make_request) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(True) == 50
    assert results.count(False) == 50
