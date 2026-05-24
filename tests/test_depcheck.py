"""Unit tests for depcheck.py."""

from __future__ import annotations

import socket
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from depcheck import (
    DepStatus,
    DepReport,
    check_tcp,
    check_http,
    run_checks,
)


# ---------------------------------------------------------------------------
# DepStatus / DepReport helpers
# ---------------------------------------------------------------------------

def test_dep_status_to_dict_ok():
    s = DepStatus(name="redis", ok=True, latency_ms=1.5)
    d = s.to_dict()
    assert d["name"] == "redis"
    assert d["ok"] is True
    assert d["latency_ms"] == 1.5
    assert d["error"] is None


def test_dep_status_to_dict_error():
    s = DepStatus(name="db", ok=False, error="connection refused")
    d = s.to_dict()
    assert d["ok"] is False
    assert d["error"] == "connection refused"


def test_dep_report_all_ok_true():
    report = DepReport(checks=[
        DepStatus(name="a", ok=True),
        DepStatus(name="b", ok=True),
    ])
    assert report.all_ok is True


def test_dep_report_all_ok_false_when_one_fails():
    report = DepReport(checks=[
        DepStatus(name="a", ok=True),
        DepStatus(name="b", ok=False),
    ])
    assert report.all_ok is False


def test_dep_report_to_dict_structure():
    report = DepReport(checks=[DepStatus(name="x", ok=True)])
    d = report.to_dict()
    assert "all_ok" in d
    assert "checks" in d
    assert len(d["checks"]) == 1


# ---------------------------------------------------------------------------
# check_tcp
# ---------------------------------------------------------------------------

def test_check_tcp_success():
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    with patch("socket.create_connection", return_value=mock_conn):
        result = check_tcp("redis", "localhost", 6379)
    assert result.ok is True
    assert result.latency_ms is not None
    assert result.error is None


def test_check_tcp_failure():
    with patch("socket.create_connection", side_effect=OSError("refused")):
        result = check_tcp("redis", "localhost", 6379)
    assert result.ok is False
    assert "refused" in result.error


# ---------------------------------------------------------------------------
# check_http
# ---------------------------------------------------------------------------

def test_check_http_success():
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = check_http("slack", "https://example.com/health")
    assert result.ok is True
    assert result.latency_ms is not None


def test_check_http_non_2xx():
    mock_resp = MagicMock()
    mock_resp.status = 503
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = check_http("slack", "https://example.com/health")
    assert result.ok is False
    assert "503" in result.error


def test_check_http_url_error():
    with patch("urllib.request.urlopen",
               side_effect=urllib.error.URLError("timeout")):
        result = check_http("slack", "https://example.com/health")
    assert result.ok is False
    assert result.error is not None


# ---------------------------------------------------------------------------
# run_checks
# ---------------------------------------------------------------------------

def test_run_checks_unknown_type():
    report = run_checks([{"type": "grpc", "name": "svc"}])
    assert report.all_ok is False
    assert "unknown check type" in report.checks[0].error


def test_run_checks_mixed():
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    with patch("socket.create_connection", return_value=mock_conn):
        report = run_checks([
            {"type": "tcp", "name": "redis", "host": "localhost", "port": 6379},
        ])
    assert len(report.checks) == 1
    assert report.checks[0].name == "redis"
