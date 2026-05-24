"""Integration tests for rollback – uses real scripts and real audit records."""
from __future__ import annotations

import os
import stat
import textwrap

import pytest

import audit
from rollback import rollback


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _reset_audit():
    audit._entries.clear()


@pytest.fixture()
def passing_script(tmp_path):
    p = tmp_path / "deploy.sh"
    p.write_text(textwrap.dedent("""\
        #!/bin/sh
        echo "deployed $DEPLOY_REF $DEPLOY_SHA"
        exit 0
    """))
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


@pytest.fixture()
def failing_script(tmp_path):
    p = tmp_path / "bad_deploy.sh"
    p.write_text(textwrap.dedent("""\
        #!/bin/sh
        echo "boom" >&2
        exit 1
    """))
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


def _seed(ref="refs/heads/main", sha="abc123", success=True):
    """Insert a synthetic audit entry."""
    import datetime
    e = audit.AuditEntry(
        timestamp=datetime.datetime.utcnow(),
        ref=ref,
        sha=sha,
        success=success,
        returncode=0 if success else 1,
        duration=0.1,
    )
    audit._entries.append(e)
    return e


# ---------------------------------------------------------------------------
# integration tests
# ---------------------------------------------------------------------------

def test_rollback_no_history_skips(passing_script):
    _reset_audit()
    result = rollback("refs/heads/main", passing_script)
    assert result.skipped is True
    assert not result.ok


def test_rollback_passing_script_succeeds(passing_script):
    _reset_audit()
    _seed(sha="goodsha", success=True)
    result = rollback("refs/heads/main", passing_script)
    assert not result.skipped
    assert result.ok
    assert result.run is not None
    assert result.run.returncode == 0


def test_rollback_uses_sha_from_last_success(passing_script):
    _reset_audit()
    _seed(sha="firstgood", success=True)
    _seed(sha="secondgood", success=True)
    _seed(sha="latestbad", success=False)
    result = rollback("refs/heads/main", passing_script)
    # Should pick secondgood (most recent success), not latestbad
    assert result.entry is not None
    assert result.entry.sha == "secondgood"


def test_rollback_failing_script_not_ok(failing_script):
    _reset_audit()
    _seed(sha="goodsha", success=True)
    result = rollback("refs/heads/main", failing_script)
    assert not result.skipped
    assert not result.ok
    assert result.run is not None
    assert result.run.returncode != 0
