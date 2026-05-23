"""Tests for cli.py argument parsing and startup logic."""

import sys
from unittest.mock import MagicMock, patch

import pytest

import cli
from cli import _parse_args, main


# ---------------------------------------------------------------------------
# _parse_args
# ---------------------------------------------------------------------------

def test_defaults():
    args = _parse_args([])
    assert args.health_port == 8081
    assert args.log_level == "INFO"
    assert args.config is None


def test_custom_health_port():
    args = _parse_args(["--health-port", "9090"])
    assert args.health_port == 9090


def test_custom_log_level():
    args = _parse_args(["--log-level", "DEBUG"])
    assert args.log_level == "DEBUG"


def test_invalid_log_level_exits(capsys):
    with pytest.raises(SystemExit):
        _parse_args(["--log-level", "VERBOSE"])


# ---------------------------------------------------------------------------
# main() — integration-style with heavy mocking
# ---------------------------------------------------------------------------

def _minimal_cfg():
    cfg = MagicMock()
    cfg.port = 8080
    return cfg


@patch("cli.HTTPServer")
@patch("cli._start_health_server")
@patch("cli.make_handler")
@patch("cli.validate")
@patch("cli.load_config")
@patch("cli.configure_root")
def test_main_returns_0_on_success(
    mock_configure, mock_load, mock_validate, mock_make_handler, mock_health, mock_httpserver
):
    mock_load.return_value = _minimal_cfg()
    mock_validate.return_value = None
    server_instance = MagicMock()
    server_instance.serve_forever.side_effect = KeyboardInterrupt
    mock_httpserver.return_value = server_instance

    result = main([])
    assert result == 0


@patch("cli.HTTPServer")
@patch("cli._start_health_server")
@patch("cli.make_handler")
@patch("cli.validate")
@patch("cli.load_config")
@patch("cli.configure_root")
def test_main_returns_1_on_invalid_config(
    mock_configure, mock_load, mock_validate, mock_make_handler, mock_health, mock_httpserver
):
    mock_load.return_value = _minimal_cfg()
    mock_validate.side_effect = ValueError("missing secret")

    result = main([])
    assert result == 1
    mock_httpserver.assert_not_called()


@patch("cli.HTTPServer")
@patch("cli._start_health_server")
@patch("cli.make_handler")
@patch("cli.validate")
@patch("cli.load_config")
@patch("cli.configure_root")
def test_health_server_always_started(
    mock_configure, mock_load, mock_validate, mock_make_handler, mock_health, mock_httpserver
):
    mock_load.return_value = _minimal_cfg()
    mock_validate.side_effect = ValueError("bad config")

    main([])
    mock_health.assert_called_once()
