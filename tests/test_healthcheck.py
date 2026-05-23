"""Tests for healthcheck.py."""

import json
import time
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

import healthcheck
from healthcheck import get_status, make_health_handler


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

def test_get_status_ok_when_config_valid():
    result = get_status(config_valid=True)
    assert result["status"] == "ok"
    assert result["config_valid"] is True


def test_get_status_degraded_when_config_invalid():
    result = get_status(config_valid=False)
    assert result["status"] == "degraded"
    assert result["config_valid"] is False


def test_get_status_contains_uptime():
    result = get_status()
    assert "uptime_seconds" in result
    assert result["uptime_seconds"] >= 0


def test_get_status_contains_version():
    result = get_status()
    assert "version" in result


def test_uptime_increases_over_time():
    first = get_status()["uptime_seconds"]
    time.sleep(0.05)
    second = get_status()["uptime_seconds"]
    assert second >= first


# ---------------------------------------------------------------------------
# make_health_handler
# ---------------------------------------------------------------------------

def _invoke_handler(path: str, config_valid: bool = True):
    """Instantiate the handler and call do_GET, returning (status, body)."""
    HandlerClass = make_health_handler(config_valid=config_valid)

    output = BytesIO()
    request = MagicMock()
    request.makefile.return_value = BytesIO(b"")

    handler = HandlerClass.__new__(HandlerClass)
    handler.path = path
    handler.wfile = output
    responses = []
    headers_sent = {}

    def fake_send_response(code):
        responses.append(code)

    def fake_send_header(k, v):
        headers_sent[k] = v

    handler.send_response = fake_send_response
    handler.send_header = fake_send_header
    handler.end_headers = MagicMock()

    handler.do_GET()
    return responses[0], output.getvalue()


def test_health_endpoint_returns_200():
    status, _ = _invoke_handler("/health")
    assert status == 200


def test_health_endpoint_returns_json():
    _, body = _invoke_handler("/health")
    data = json.loads(body)
    assert data["status"] == "ok"


def test_unknown_path_returns_404():
    status, body = _invoke_handler("/unknown")
    assert status == 404


def test_health_degraded_reflected_in_body():
    _, body = _invoke_handler("/health", config_valid=False)
    data = json.loads(body)
    assert data["status"] == "degraded"
