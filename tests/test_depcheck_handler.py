"""Tests for depcheck_handler.py."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

import depcheck_handler as dh
from depcheck_handler import configure, make_dep_handler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_handler(path: str = "/deps"):
    """Construct a DepHandler instance with a fake request."""
    Handler = make_dep_handler()
    handler = Handler.__new__(Handler)
    handler.path = path
    handler.wfile = io.BytesIO()
    handler._headers_buffer = []
    handler._response_code = None

    def _send_response(code):
        handler._response_code = code

    def _send_header(k, v):
        handler._headers_buffer.append((k, v))

    def _end_headers():
        pass

    handler.send_response = _send_response
    handler.send_header = _send_header
    handler.end_headers = _end_headers
    return handler


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------

def test_configure_sets_checks():
    configure([{"type": "tcp", "name": "r", "host": "h", "port": 1}])
    assert dh._CHECKS[0]["name"] == "r"
    configure([])  # reset


# ---------------------------------------------------------------------------
# do_GET /deps
# ---------------------------------------------------------------------------

def test_get_deps_returns_200_when_all_ok():
    configure([])
    handler = _make_handler("/deps")
    handler.do_GET()
    assert handler._response_code == 200
    handler.wfile.seek(0)
    data = json.loads(handler.wfile.read())
    assert data["all_ok"] is True


def test_get_deps_returns_503_when_check_fails():
    configure([{"type": "tcp", "name": "dead", "host": "127.0.0.1", "port": 1}])
    with patch("socket.create_connection", side_effect=OSError("refused")):
        handler = _make_handler("/deps")
        handler.do_GET()
    configure([])
    assert handler._response_code == 503
    handler.wfile.seek(0)
    data = json.loads(handler.wfile.read())
    assert data["all_ok"] is False


def test_get_unknown_path_returns_404():
    configure([])
    handler = _make_handler("/unknown")
    handler.do_GET()
    assert handler._response_code == 404


def test_response_body_is_valid_json():
    configure([])
    handler = _make_handler("/deps")
    handler.do_GET()
    handler.wfile.seek(0)
    raw = handler.wfile.read()
    parsed = json.loads(raw)
    assert "checks" in parsed


def test_content_type_header_set():
    configure([])
    handler = _make_handler("/deps")
    handler.do_GET()
    headers = dict(handler._headers_buffer)
    assert headers.get("Content-Type") == "application/json"
