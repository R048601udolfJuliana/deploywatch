"""Tests for middleware.py"""

import io
import pytest
from unittest.mock import MagicMock, patch
import middleware
from middleware import check_rate_limit, client_ip, configure, get_limiter
from ratelimit import RateLimiter


def _make_handler(ip="1.2.3.4", forwarded=None):
    handler = MagicMock()
    handler.client_address = (ip, 12345)
    headers = {}
    if forwarded:
        headers["X-Forwarded-For"] = forwarded
    handler.headers = headers
    handler.wfile = io.BytesIO()
    return handler


@pytest.fixture(autouse=True)
def reset_limiter():
    """Ensure each test starts with a fresh limiter."""
    middleware._limiter = None
    yield
    middleware._limiter = None


def test_configure_returns_rate_limiter():
    rl = configure(max_requests=5, window_seconds=30)
    assert isinstance(rl, RateLimiter)
    assert rl.max_requests == 5
    assert rl.window_seconds == 30


def test_get_limiter_creates_default_when_none():
    middleware._limiter = None
    rl = get_limiter()
    assert isinstance(rl, RateLimiter)


def test_get_limiter_returns_existing():
    existing = configure(max_requests=99)
    assert get_limiter() is existing


def test_client_ip_from_address():
    handler = _make_handler(ip="192.168.1.1")
    assert client_ip(handler) == "192.168.1.1"


def test_client_ip_prefers_x_forwarded_for():
    handler = _make_handler(ip="10.0.0.1", forwarded="203.0.113.5, 10.0.0.1")
    assert client_ip(handler) == "203.0.113.5"


def test_client_ip_strips_whitespace():
    handler = _make_handler(forwarded="  203.0.113.5  ")
    assert client_ip(handler) == "203.0.113.5"


def test_check_rate_limit_allows_under_limit():
    configure(max_requests=5)
    handler = _make_handler()
    assert check_rate_limit(handler) is True
    handler.send_response.assert_not_called()


def test_check_rate_limit_denies_over_limit():
    configure(max_requests=2)
    handler = _make_handler()
    check_rate_limit(handler)
    check_rate_limit(handler)
    result = check_rate_limit(handler)
    assert result is False
    handler.send_response.assert_called_with(429)


def test_check_rate_limit_writes_json_body():
    configure(max_requests=1)
    handler = _make_handler()
    check_rate_limit(handler)  # consume the one allowed request
    check_rate_limit(handler)  # this should be denied
    handler.wfile.seek(0)
    body = handler.wfile.read()
    assert b"rate limit exceeded" in body


def test_check_rate_limit_sets_headers_on_deny():
    configure(max_requests=1)
    handler = _make_handler()
    check_rate_limit(handler)
    check_rate_limit(handler)
    calls = [str(c) for c in handler.send_header.call_args_list]
    assert any("X-RateLimit-Limit" in c for c in calls)
    assert any("X-RateLimit-Remaining" in c for c in calls)
