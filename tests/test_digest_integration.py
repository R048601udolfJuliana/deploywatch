"""Integration tests for digest + notifier pipeline."""

from __future__ import annotations

import datetime
from unittest.mock import patch, MagicMock

import pytest

import audit
from audit import AuditEntry
import digest as digest_mod
from notifier import send_notification


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_audit():
    audit._entries.clear()  # type: ignore[attr-defined]
    yield
    audit._entries.clear()  # type: ignore[attr-defined]


def _seed(ref: str = "refs/heads/main", success: bool = True, minutes_ago: float = 5):
    ts = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes_ago)
    entry = AuditEntry(
        timestamp=ts,
        ref=ref,
        success=success,
        returncode=0 if success else 1,
        duration=2.3,
        script="deploy.sh",
    )
    audit.record(entry)
    return entry


# ---------------------------------------------------------------------------
# integration: build_digest reflects audit state
# ---------------------------------------------------------------------------

def test_digest_reflects_seeded_entries():
    _seed(success=True)
    _seed(success=True)
    _seed(success=False)
    d = digest_mod.build_digest(window_minutes=60)
    assert d["total"] == 3
    assert d["successes"] == 2
    assert d["failures"] == 1


def test_digest_entries_contain_expected_fields():
    _seed(ref="refs/heads/feature", success=True)
    d = digest_mod.build_digest(window_minutes=60)
    assert len(d["entries"]) == 1
    entry_dict = d["entries"][0]
    assert "ref" in entry_dict
    assert "success" in entry_dict
    assert entry_dict["ref"] == "refs/heads/feature"


# ---------------------------------------------------------------------------
# integration: slack payload sent via notifier
# ---------------------------------------------------------------------------

def test_slack_digest_sent_via_notifier():
    _seed(success=True)
    d = digest_mod.build_digest(window_minutes=60)
    payload = digest_mod.format_slack_digest(d)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"ok"

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        result = send_notification(
            webhook_url="https://hooks.slack.com/fake",
            payload=payload,
        )
    assert result is True
    mock_open.assert_called_once()


def test_no_entries_produces_valid_slack_payload():
    # empty audit window — should still produce a valid payload without error
    d = digest_mod.build_digest(window_minutes=60)
    payload = digest_mod.format_slack_digest(d)
    ref_block_text = payload["blocks"][1]["text"]["text"]
    assert "no deploys" in ref_block_text
