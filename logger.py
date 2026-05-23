"""Structured logging utilities for deploywatch."""

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Optional


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": _utcnow(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Merge any extra fields passed via the `extra` kwarg
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload)


def get_logger(
    name: str,
    level: int = logging.INFO,
    json_output: bool = True,
) -> logging.Logger:
    """Return a named logger, optionally with JSON formatting.

    Args:
        name: Logger name (typically __name__ of the calling module).
        level: Logging level, e.g. logging.DEBUG.
        json_output: When True, emit JSON lines; plain text otherwise.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def configure_root(
    level: int = logging.INFO,
    json_output: bool = True,
) -> None:
    """Configure the root logger (called once at application startup)."""
    get_logger("deploywatch", level=level, json_output=json_output)
