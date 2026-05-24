"""Integration tests: deploylock interacting with runner.run_script."""
from __future__ import annotations

import stat
import textwrap
from pathlib import Path

import pytest

import deploylock
from deploylock import DeployLockError, acquire, check, release, _reset
from runner import run_script


@pytest.fixture(autouse=True)
def reset_lock():
    _reset()
    yield
    _reset()


@pytest.fixture()
def passing_script(tmp_path: Path) -> Path:
    s = tmp_path / "deploy.sh"
    s.write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        echo "deployed"
        exit 0
    """))
    s.chmod(s.stat().st_mode | stat.S_IEXEC)
    return s


def _guarded_deploy(script: Path, ref: str) -> None:
    """Simulate a deploy that respects the global lock."""
    check()  # raises DeployLockError if locked
    run_script(str(script), ref)


def test_deploy_succeeds_when_unlocked(passing_script):
    result = run_script(str(passing_script), "refs/heads/main")
    assert result.returncode == 0


def test_deploy_blocked_when_locked(passing_script):
    acquire("ops", reason="maintenance window")
    with pytest.raises(DeployLockError):
        _guarded_deploy(passing_script, "refs/heads/main")


def test_deploy_resumes_after_release(passing_script):
    acquire("ops")
    release()
    # should not raise
    _guarded_deploy(passing_script, "refs/heads/main")


def test_lock_status_reflects_operator(passing_script):
    acquire("release-bot", reason="scheduled")
    s = deploylock.status()
    assert s["locked_by"] == "release-bot"
    assert s["reason"] == "scheduled"
