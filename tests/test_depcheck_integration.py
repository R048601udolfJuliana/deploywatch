"""Integration tests for depcheck — exercises run_checks end-to-end with a
real TCP server (loopback) and a mock HTTP endpoint."""

from __future__ import annotations

import socket
import threading
import time
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from depcheck import run_checks, DepReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _start_echo_server(port: int) -> threading.Thread:
    """Bind a TCP socket and accept one connection then close."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", port))
    srv.listen(1)
    srv.settimeout(3)

    def _serve():
        try:
            conn, _ = srv.accept()
            conn.close()
        except Exception:
            pass
        finally:
            srv.close()

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    return t


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_tcp_check_against_real_socket():
    port = _free_port()
    t = _start_echo_server(port)
    time.sleep(0.05)  # let server bind

    report = run_checks([{"type": "tcp", "name": "loopback", "host": "127.0.0.1", "port": port}])
    t.join(timeout=2)

    assert report.all_ok is True
    assert report.checks[0].latency_ms is not None


def test_tcp_check_refused_port():
    port = _free_port()  # nothing listening
    report = run_checks([{"type": "tcp", "name": "dead", "host": "127.0.0.1", "port": port}])
    assert report.all_ok is False
    assert report.checks[0].error is not None


def test_http_check_success_via_mock():
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        report = run_checks([{"type": "http", "name": "api", "url": "http://localhost/health"}])

    assert report.all_ok is True
    assert report.checks[0].name == "api"


def test_mixed_checks_partial_failure():
    port = _free_port()  # nothing listening — TCP will fail
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        report = run_checks([
            {"type": "tcp", "name": "dead", "host": "127.0.0.1", "port": port},
            {"type": "http", "name": "api",  "url": "http://localhost/health"},
        ])

    assert report.all_ok is False
    names = {c.name: c for c in report.checks}
    assert names["dead"].ok is False
    assert names["api"].ok is True


def test_report_to_dict_is_json_serialisable():
    import json
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        report = run_checks([{"type": "http", "name": "x", "url": "http://h/"}])

    blob = json.dumps(report.to_dict())
    parsed = json.loads(blob)
    assert "all_ok" in parsed
    assert isinstance(parsed["checks"], list)
