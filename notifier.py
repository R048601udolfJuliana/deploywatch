"""Slack notification module for deploywatch."""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def _build_payload(repo: str, branch: str, pusher: str, commit: str, success: bool) -> dict:
    """Build a Slack message payload for a deploy event."""
    status_emoji = ":white_check_mark:" if success else ":x:"
    status_text = "succeeded" if success else "failed"
    color = "#36a64f" if success else "#ff0000"

    return {
        "attachments": [
            {
                "color": color,
                "fallback": f"Deploy {status_text} for {repo}@{branch}",
                "title": f"{status_emoji} Deploy {status_text}",
                "fields": [
                    {"title": "Repository", "value": repo, "short": True},
                    {"title": "Branch", "value": branch, "short": True},
                    {"title": "Pusher", "value": pusher, "short": True},
                    {"title": "Commit", "value": commit[:7], "short": True},
                ],
                "footer": "deploywatch",
            }
        ]
    }


def send_notification(
    webhook_url: str,
    repo: str,
    branch: str,
    pusher: str,
    commit: str,
    success: bool,
    timeout: int = 5,
) -> bool:
    """Send a Slack notification for a deploy event.

    Returns True if the notification was sent successfully, False otherwise.
    """
    if not webhook_url:
        logger.debug("No Slack webhook URL configured; skipping notification.")
        return False

    payload = _build_payload(repo, branch, pusher, commit, success)

    try:
        response = requests.post(webhook_url, json=payload, timeout=timeout)
        response.raise_for_status()
        logger.info("Slack notification sent (repo=%s branch=%s success=%s)", repo, branch, success)
        return True
    except requests.RequestException as exc:
        logger.error("Failed to send Slack notification: %s", exc)
        return False
