"""Tests for audit.py."""

import time
import pytest
import audit
from audit import AuditEntry, record, recent, clear, as_json
import json


@pytest.fixture(autouse=True)
def _reset():
    clear()
    yield
    clear()


def _entry(**kwargs) -> AuditEntry:
    defaults = dict(event="push", repository="acme/app", ref="refs/heads/main")
    defaults.update(kwargs)
    return AuditEntry(**defaults)


def test_record_stores_entry():
    record(_entry())
    entries = recent()
    assert len(entries) == 1
    assert entries[0]["repository"] == "acme/app"


def test_recent_returns_newest_first():
    record(_entry(ref="refs/heads/first"))
    record(_entry(ref="refs/heads/second"))
    entries = recent()
    assert entries[0]["ref"] == "refs/heads/second"
    assert entries[1]["ref"] == "refs/heads/first"


def test_recent_respects_limit():
    for i in range(10):
        record(_entry(ref=f"refs/heads/branch-{i}"))
    assert len(recent(limit=5)) == 5


def test_clear_removes_all_entries():
    record(_entry())
    clear()
    assert recent() == []


def test_none_fields_omitted_from_dict():
    e = _entry()
    d = e.to_dict()
    assert "script_exit_code" not in d
    assert "error" not in d


def test_optional_fields_included_when_set():
    e = _entry(script_exit_code=0, notified=True, client_ip="10.0.0.1")
    d = e.to_dict()
    assert d["script_exit_code"] == 0
    assert d["notified"] is True
    assert d["client_ip"] == "10.0.0.1"


def test_delivered_at_is_iso8601():
    e = _entry()
    record(e)
    entry = recent(1)[0]
    # Should parse without error
    from datetime import datetime
    datetime.fromisoformat(entry["delivered_at"])


def test_cap_at_max_entries(monkeypatch):
    monkeypatch.setattr(audit, "_MAX_ENTRIES", 5)
    for i in range(10):
        record(_entry(ref=f"refs/heads/b{i}"))
    assert len(recent(limit=100)) == 5


def test_as_json_returns_valid_json():
    record(_entry())
    data = json.loads(as_json())
    assert isinstance(data, list)
    assert data[0]["event"] == "push"


def test_as_json_empty_when_no_entries():
    data = json.loads(as_json())
    assert data == []
