"""WSGI-style middleware utilities applied inside WebhookHandler."""

import logging
from http.server import BaseHTTPRequestHandler
from ratelimit import RateLimiter

logger = logging.getLogger(__name__)

# Module-level default limiter; can be replaced in tests or via configure().
_limiter: RateLimiter | None = None


def configure(max_requests: int = 30, window_seconds: float = 60.0) -> RateLimiter:
    """Initialise (or replace) the module-level rate limiter and return it."""
    global _limiter
    _limiter = RateLimiter(max_requests=max_requests, window_seconds=window_seconds)
    logger.info(
        "Rate limiter configured",
        extra={"max_requests": max_requests, "window_seconds": window_seconds},
    )
    return _limiter


def get_limiter() -> RateLimiter:
    """Return the module-level limiter, creating a default one if needed."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def client_ip(handler: BaseHTTPRequestHandler) -> str:
    """Extract the client IP from a request handler, honouring X-Forwarded-For."""
    forwarded = handler.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    address = handler.client_address
    return address[0] if address else "unknown"


def check_rate_limit(handler: BaseHTTPRequestHandler) -> bool:
    """
    Check whether *handler*'s client is within the rate limit.

    Sends a 429 response and returns False when the limit is exceeded,
    otherwise returns True.
    """
    ip = client_ip(handler)
    limiter = get_limiter()
    if limiter.is_allowed(ip):
        return True

    remaining_after_reset = limiter.remaining(ip)
    logger.warning("Rate limit exceeded", extra={"client_ip": ip})
    handler.send_response(429)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("X-RateLimit-Limit", str(limiter.max_requests))
    handler.send_header("X-RateLimit-Remaining", str(remaining_after_reset))
    handler.end_headers()
    handler.wfile.write(b'{"error": "rate limit exceeded"}')
    return False
