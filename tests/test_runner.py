"""Tests for runner.py."""

import stat
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runner import RunResult, run_script


@pytest.fixture()
def script_factory(tmp_path):
    """Return a helper that creates executable shell scripts."""

    def _make(name: str, body: str, executable: bool = True) -> Path:
        p = tmp_path / name
        p.write_text(textwrap.dedent(body))
        if executable:
            p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return p

    return _make


def test_run_script_success(script_factory):
    script = script_factory("deploy.sh", """\
        #!/bin/sh
        echo hello
        exit 0
    """)
    result = run_script(str(script))
    assert result.success is True
    assert result.exit_code == 0
    assert "hello" in result.stdout
    assert result.duration >= 0
    assert result.error is None


def test_run_script_failure(script_factory):
    script = script_factory("fail.sh", """\
        #!/bin/sh
        echo oops >&2
        exit 1
    """)
    result = run_script(str(script))
    assert result.success is False
    assert result.exit_code == 1
    assert "oops" in result.stderr


def test_run_script_not_found():
    result = run_script("/nonexistent/deploy.sh")
    assert result.success is False
    assert result.exit_code == -1
    assert result.error is not None
    assert "not found" in result.error


def test_run_script_not_executable(script_factory):
    script = script_factory("nodeploy.sh", "#!/bin/sh\necho hi", executable=False)
    result = run_script(str(script))
    assert result.success is False
    assert result.exit_code == -1
    assert "not executable" in (result.error or "")


def test_run_script_timeout(script_factory):
    script = script_factory("slow.sh", """\
        #!/bin/sh
        sleep 30
    """)
    result = run_script(str(script), timeout=1)
    assert result.success is False
    assert result.exit_code == -1
    assert result.error is not None
    assert "Timed out" in result.error


def test_run_result_summary_success():
    r = RunResult(script="deploy.sh", success=True, exit_code=0,
                  stdout="ok", stderr="", duration=1.23)
    assert "succeeded" in r.summary
    assert "deploy.sh" in r.summary
    assert "1.23" in r.summary


def test_run_result_summary_failure():
    r = RunResult(script="deploy.sh", success=False, exit_code=1,
                  stdout="", stderr="err", duration=0.5)
    assert "failed" in r.summary
    assert "exit 1" in r.summary
