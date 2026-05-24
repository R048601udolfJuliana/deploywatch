"""Integration tests for replay — uses real audit entries and a real script."""

from __future__ import annotations

import os
import stat
import textwrap
from pathlib import Path

import pytest

import audit
from replay import replay_recent, summary


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_audit():
    """Wipe audit log before each test."""
    audit._entries.clear()  # type: ignore[attr-defined]
    yield
    audit._entries.clear()  # type: ignore[attr-defined]


@pytest.fixture()
def passing_script(tmp_path: Path) -> str:
    script = tmp_path / "pass.sh"
    script.write_text(textwrap.dedent("""\
        #!/bin/sh
        echo "replayed $REPLAY_EVENT_ID"
        exit 0
    """))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


@pytest.fixture()
def failing_script(tmp_path: Path) -> str:
    script = tmp_path / "fail.sh"
    script.write_text(textwrap.dedent("""\
        #!/bin/sh
        exit 1
    """))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


def _seed_entries(n: int = 2):
    for i in range(n):
        audit.record(
            event_id=f"evt-{i}",
            ref="refs/heads/main",
            pusher="tester",
            status="success",
        )


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_integration_passing_script_all_ok(passing_script):
    _seed_entries(2)
    results = replay_recent(passing_script, limit=2)
    assert all(r.ok for r in results)


def test_integration_failing_script_none_ok(failing_script):
    _seed_entries(2)
    results = replay_recent(failing_script, limit=2)
    assert not any(r.ok for r in results)


def test_integration_dry_run_no_side_effects(passing_script, monkeypatch):
    calls = []
    monkeypatch.setattr("replay.run_script", lambda *a, **kw: calls.append((a, kw)))
    _seed_entries(3)
    results = replay_recent(passing_script, limit=3, dry_run=True)
    assert calls == []
    assert len(results) == 3


def test_integration_summary_string(passing_script):
    _seed_entries(2)
    results = replay_recent(passing_script, limit=2)
    s = summary(results)
    assert s.startswith("replayed 2")
    assert "2 ok" in s
