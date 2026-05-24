"""Unit tests for digest.py."""

from __future__ import annotations

import datetime
import types
from unittest.mock import patch

import pytest

import audit
import digest as digest_mod
from audit import AuditEntry


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _reset():
    audit._entries.clear()  # type: ignore[attr-defined]


def _entry(
    ref: str = "refs/heads/main",
    success: bool = True,
    minutes_ago: float = 5,
) -> AuditEntry:
    ts = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes_ago)
    return AuditEntry(
        timestamp=ts,
        ref=ref,
        success=success,
        returncode=0 if success else 1,
        duration=1.0,
        script="deploy.sh",
    )


# ---------------------------------------------------------------------------
# build_digest
# ---------------------------------------------------------------------------

def test_empty_audit_returns_zero_counts():
    _reset()
    d = digest_mod.build_digest(window_minutes=60)
    assert d["total"] == 0
    assert d["successes"] == 0
    assert d["failures"] == 0


def test_counts_successes_and_failures():
    _reset()
    audit.record(_entry(success=True))
    audit.record(_entry(success=True))
    audit.record(_entry(success=False))
    d = digest_mod.build_digest(window_minutes=60)
    assert d["total"] == 3
    assert d["successes"] == 2
    assert d["failures"] == 1


def test_window_excludes_old_entries():
    _reset()
    audit.record(_entry(minutes_ago=10))
    audit.record(_entry(minutes_ago=120))  # outside 60-min window
    d = digest_mod.build_digest(window_minutes=60)
    assert d["total"] == 1


def test_refs_aggregated():
    _reset()
    audit.record(_entry(ref="refs/heads/main"))
    audit.record(_entry(ref="refs/heads/main"))
    audit.record(_entry(ref="refs/heads/dev"))
    d = digest_mod.build_digest(window_minutes=60)
    assert d["refs"]["refs/heads/main"] == 2
    assert d["refs"]["refs/heads/dev"] == 1


def test_generated_at_is_string():
    _reset()
    d = digest_mod.build_digest()
    assert isinstance(d["generated_at"], str)
    assert d["generated_at"].endswith("Z")


# ---------------------------------------------------------------------------
# format_slack_digest
# ---------------------------------------------------------------------------

def test_slack_payload_has_blocks():
    d = digest_mod.build_digest.__wrapped__ if hasattr(digest_mod.build_digest, "__wrapped__") else None
    raw = {
        "window_minutes": 60,
        "generated_at": "2024-01-01T00:00:00Z",
        "total": 2,
        "successes": 2,
        "failures": 0,
        "refs": {"refs/heads/main": 2},
        "entries": [],
    }
    payload = digest_mod.format_slack_digest(raw)
    assert "blocks" in payload
    assert len(payload["blocks"]) == 3


def test_slack_payload_warning_on_failure():
    raw = {
        "window_minutes": 60,
        "generated_at": "2024-01-01T00:00:00Z",
        "total": 1,
        "successes": 0,
        "failures": 1,
        "refs": {},
        "entries": [],
    }
    payload = digest_mod.format_slack_digest(raw)
    header_text = payload["blocks"][0]["text"]["text"]
    assert ":warning:" in header_text


def test_slack_payload_ok_emoji_when_no_failures():
    raw = {
        "window_minutes": 30,
        "generated_at": "2024-01-01T00:00:00Z",
        "total": 1,
        "successes": 1,
        "failures": 0,
        "refs": {"refs/heads/main": 1},
        "entries": [],
    }
    payload = digest_mod.format_slack_digest(raw)
    header_text = payload["blocks"][0]["text"]["text"]
    assert ":white_check_mark:" in header_text
