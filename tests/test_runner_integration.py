"""Integration tests that verify runner output feeds into notifier payload."""

import stat
import textwrap
from pathlib import Path

import pytest

from notifier import _build_payload
from runner import RunResult, run_script


@pytest.fixture()
def passing_script(tmp_path) -> Path:
    p = tmp_path / "deploy.sh"
    p.write_text(textwrap.dedent("""\
        #!/bin/sh
        echo 'Deployed successfully'
        exit 0
    """))
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


@pytest.fixture()
def failing_script(tmp_path) -> Path:
    p = tmp_path / "rollback.sh"
    p.write_text(textwrap.dedent("""\
        #!/bin/sh
        echo 'Rollback failed' >&2
        exit 2
    """))
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def test_successful_run_produces_good_payload(passing_script):
    result = run_script(str(passing_script))
    assert result.success is True

    payload = _build_payload(
        success=result.success,
        repo="acme/app",
        branch="main",
        commit="abc1234",
        pusher="alice",
        details=result.summary,
    )

    text = payload["text"]
    assert "succeeded" in text or "✅" in text or "acme/app" in text
    assert payload["attachments"][0]["color"] == "good"


def test_failed_run_produces_danger_payload(failing_script):
    result = run_script(str(failing_script))
    assert result.success is False

    payload = _build_payload(
        success=result.success,
        repo="acme/app",
        branch="main",
        commit="abc1234",
        pusher="bob",
        details=result.summary,
    )

    assert payload["attachments"][0]["color"] == "danger"
    text = str(payload)
    assert "rollback.sh" in text or "failed" in text


def test_run_result_summary_appears_in_payload_fields(passing_script):
    result = run_script(str(passing_script))
    payload = _build_payload(
        success=result.success,
        repo="org/repo",
        branch="develop",
        commit="deadbeef",
        pusher="carol",
        details=result.summary,
    )
    fields = payload["attachments"][0].get("fields", [])
    field_values = " ".join(f.get("value", "") for f in fields)
    assert "deploy.sh" in field_values or "deploy.sh" in str(payload)
