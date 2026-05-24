"""Integration tests: DeployLockout wired into a simulated deploy loop."""

import subprocess
import sys
import textwrap
import os
import stat
import pytest

from lockout import DeployLockout, LockoutError
from runner import run_script


@pytest.fixture()
def passing_script(tmp_path):
    p = tmp_path / "deploy_ok.sh"
    p.write_text(textwrap.dedent("""\
        #!/bin/sh
        echo "deployed successfully"
        exit 0
    """))
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


@pytest.fixture()
def failing_script(tmp_path):
    p = tmp_path / "deploy_fail.sh"
    p.write_text(textwrap.dedent("""\
        #!/bin/sh
        echo "deployment failed" >&2
        exit 1
    """))
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return str(p)


def _deploy(lockout: DeployLockout, ref: str, script: str) -> bool:
    """Simulate a deploy: check lockout, run script, record result."""
    lockout.check(ref)            # raises LockoutError if blocked
    result = run_script(script)   # runner.RunResult
    if result.returncode == 0:
        lockout.record_success(ref)
        return True
    else:
        lockout.record_failure(ref)
        return False


def test_passing_deploy_clears_failures(passing_script):
    lo = DeployLockout(threshold=3, window=60.0, duration=300.0)
    lo.record_failure("main")
    lo.record_failure("main")
    assert lo.status("main")["failures"] == 2

    ok = _deploy(lo, "main", passing_script)
    assert ok is True
    assert lo.status("main")["failures"] == 0
    assert lo.is_locked("main") is False


def test_repeated_failures_trigger_lockout(failing_script):
    lo = DeployLockout(threshold=3, window=60.0, duration=300.0)
    for _ in range(3):
        ok = _deploy(lo, "main", failing_script)
        assert ok is False

    assert lo.is_locked("main") is True
    with pytest.raises(LockoutError):
        _deploy(lo, "main", failing_script)


def test_different_refs_are_independent(failing_script, passing_script):
    lo = DeployLockout(threshold=2, window=60.0, duration=300.0)
    # lock out "feature"
    _deploy(lo, "feature", failing_script)
    _deploy(lo, "feature", failing_script)
    assert lo.is_locked("feature") is True

    # "main" should still be fine
    assert lo.is_locked("main") is False
    ok = _deploy(lo, "main", passing_script)
    assert ok is True


def test_lockout_status_unlocks_in_positive(failing_script):
    lo = DeployLockout(threshold=2, window=60.0, duration=300.0)
    _deploy(lo, "main", failing_script)
    _deploy(lo, "main", failing_script)
    s = lo.status("main")
    assert s["locked"] is True
    assert s["unlocks_in"] > 0
