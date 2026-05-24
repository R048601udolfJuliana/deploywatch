"""Integration tests for redeploy.py using real scripts."""
from __future__ import annotations

import datetime
import os
import stat
import tempfile

import pytest

import audit
from redeploy import redeploy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _reset_audit():
    audit._entries.clear()


def _seed(ref: str, success: bool = True):
    audit._entries.appendleft(
        audit.AuditEntry(
            ref=ref,
            script="deploy.sh",
            success=success,
            timestamp=datetime.datetime.utcnow().isoformat(),
            duration=0.1,
            stdout="",
            stderr="",
            returncode=0 if success else 1,
        )
    )


@pytest.fixture()
def passing_script():
    with tempfile.NamedTemporaryFile(suffix=".sh", delete=False, mode="w") as f:
        f.write("#!/bin/sh\necho 'deployed'\nexit 0\n")
        path = f.name
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    yield path
    os.unlink(path)


@pytest.fixture()
def failing_script():
    with tempfile.NamedTemporaryFile(suffix=".sh", delete=False, mode="w") as f:
        f.write("#!/bin/sh\necho 'boom' >&2\nexit 1\n")
        path = f.name
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    yield path
    os.unlink(path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_redeploy_no_history_skips(passing_script):
    _reset_audit()
    result = redeploy("refs/heads/main", script=passing_script)
    assert result.skipped is True
    assert not result.ok


def test_redeploy_passing_script_succeeds(passing_script):
    _reset_audit()
    _seed("refs/heads/main")
    result = redeploy("refs/heads/main", script=passing_script, timeout=10)
    assert not result.skipped
    assert result.ok
    assert result.run is not None
    assert "deployed" in result.run.stdout


def test_redeploy_failing_script_not_ok(failing_script):
    _reset_audit()
    _seed("refs/heads/main")
    result = redeploy("refs/heads/main", script=failing_script, timeout=10)
    assert not result.skipped
    assert not result.ok
    assert result.run.returncode == 1
    assert "boom" in result.run.stderr


def test_redeploy_only_matches_correct_ref(passing_script):
    _reset_audit()
    _seed("refs/heads/other")
    result = redeploy("refs/heads/main", script=passing_script)
    assert result.skipped is True
    assert "refs/heads/main" in result.skip_reason
