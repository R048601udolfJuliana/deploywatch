"""Tests for the notifier module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from notifier import _build_payload, send_notification


EVENT = {
    "repo": "acme/myapp",
    "branch": "main",
    "pusher": "alice",
    "commit": "abc1234def5678",
}


def test_build_payload_success():
    payload = _build_payload(**EVENT, success=True)
    attachment = payload["attachments"][0]
    assert attachment["color"] == "#36a64f"
    assert "succeeded" in attachment["title"]
    assert ":white_check_mark:" in attachment["title"]
    fields = {f["title"]: f["value"] for f in attachment["fields"]}
    assert fields["Repository"] == "acme/myapp"
    assert fields["Branch"] == "main"
    assert fields["Pusher"] == "alice"
    assert fields["Commit"] == "abc1234"  # truncated to 7 chars


def test_build_payload_failure():
    payload = _build_payload(**EVENT, success=False)
    attachment = payload["attachments"][0]
    assert attachment["color"] == "#ff0000"
    assert "failed" in attachment["title"]
    assert ":x:" in attachment["title"]


def test_send_notification_no_url_returns_false():
    result = send_notification("", **EVENT, success=True)
    assert result is False


@patch("notifier.requests.post")
def test_send_notification_success(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = send_notification("https://hooks.slack.com/xxx", **EVENT, success=True)

    assert result is True
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["timeout"] == 5


@patch("notifier.requests.post")
def test_send_notification_http_error_returns_false(mock_post):
    mock_post.side_effect = requests.RequestException("connection refused")

    result = send_notification("https://hooks.slack.com/xxx", **EVENT, success=False)

    assert result is False


@patch("notifier.requests.post")
def test_send_notification_custom_timeout(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    send_notification("https://hooks.slack.com/xxx", **EVENT, success=True, timeout=10)

    assert mock_post.call_args.kwargs["timeout"] == 10
