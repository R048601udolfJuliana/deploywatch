"""Tests for logger.py."""

import json
import logging
import pytest

from logger import JsonFormatter, get_logger, configure_root


# ---------------------------------------------------------------------------
# JsonFormatter
# ---------------------------------------------------------------------------

def _make_record(msg: str, level: int = logging.INFO, extra: dict | None = None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for k, v in (extra or {}).items():
        setattr(record, k, v)
    return record


def test_json_formatter_produces_valid_json():
    fmt = JsonFormatter()
    output = fmt.format(_make_record("hello"))
    data = json.loads(output)  # must not raise
    assert data["msg"] == "hello"


def test_json_formatter_contains_required_keys():
    fmt = JsonFormatter()
    data = json.loads(fmt.format(_make_record("x")))
    for key in ("ts", "level", "logger", "msg"):
        assert key in data


def test_json_formatter_merges_extra_fields():
    fmt = JsonFormatter()
    record = _make_record("deploy", extra={"repo": "acme/app", "ref": "refs/heads/main"})
    data = json.loads(fmt.format(record))
    assert data["repo"] == "acme/app"
    assert data["ref"] == "refs/heads/main"


def test_json_formatter_level_name():
    fmt = JsonFormatter()
    data = json.loads(fmt.format(_make_record("err", level=logging.ERROR)))
    assert data["level"] == "ERROR"


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------

def test_get_logger_returns_logger_instance():
    logger = get_logger("deploywatch.test_get")
    assert isinstance(logger, logging.Logger)


def test_get_logger_idempotent():
    """Calling get_logger twice for the same name must not add duplicate handlers."""
    name = "deploywatch.idempotent"
    logger1 = get_logger(name)
    logger2 = get_logger(name)
    assert logger1 is logger2
    assert len(logger1.handlers) == 1


def test_get_logger_plain_text(capsys):
    logger = get_logger("deploywatch.plain", json_output=False)
    logger.info("plain message")
    captured = capsys.readouterr()
    assert "plain message" in captured.out
    # Should NOT be valid JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured.out.strip())


def test_get_logger_json_output(capsys):
    logger = get_logger("deploywatch.jsonout", json_output=True)
    logger.warning("json message")
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["msg"] == "json message"
    assert data["level"] == "WARNING"


# ---------------------------------------------------------------------------
# configure_root
# ---------------------------------------------------------------------------

def test_configure_root_does_not_raise():
    configure_root(level=logging.DEBUG, json_output=True)
    root = logging.getLogger("deploywatch")
    assert root.level == logging.DEBUG
