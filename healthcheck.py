"""Simple health check endpoint for deploywatch."""

import json
import time
from http.server import BaseHTTPRequestHandler
from typing import Dict, Any

_START_TIME: float = time.time()


def get_status(config_valid: bool = True) -> Dict[str, Any]:
    """Return a dict describing current service health."""
    return {
        "status": "ok" if config_valid else "degraded",
        "uptime_seconds": round(time.time() - _START_TIME, 2),
        "config_valid": config_valid,
        "version": "1.0.0",
    }


def make_health_handler(config_valid: bool = True):
    """Return a BaseHTTPRequestHandler subclass that serves /health."""

    class HealthHandler(BaseHTTPRequestHandler):
        """Handles GET /health requests."""

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/health":
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
                return

            payload = get_status(config_valid)
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:  # noqa: ANN002
            """Suppress default HTTP server logging."""

    return HealthHandler
