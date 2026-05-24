"""Periodic deploy digest: summarise recent audit entries into a report."""

from __future__ import annotations

import datetime
from typing import List, Dict, Any

from audit import AuditEntry, recent as audit_recent


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


def build_digest(window_minutes: int = 60, limit: int = 100) -> Dict[str, Any]:
    """Return a digest dict covering the last *window_minutes* of audit entries."""
    cutoff = _utcnow() - datetime.timedelta(minutes=window_minutes)
    entries: List[AuditEntry] = [
        e for e in audit_recent(limit) if e.timestamp >= cutoff
    ]

    total = len(entries)
    successes = sum(1 for e in entries if e.success)
    failures = total - successes
    refs: Dict[str, int] = {}
    for e in entries:
        refs[e.ref] = refs.get(e.ref, 0) + 1

    return {
        "window_minutes": window_minutes,
        "generated_at": _utcnow().isoformat() + "Z",
        "total": total,
        "successes": successes,
        "failures": failures,
        "refs": refs,
        "entries": [e.to_dict() for e in entries],
    }


def format_slack_digest(digest: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a digest dict into a Slack Block Kit payload."""
    status_emoji = ":white_check_mark:" if digest["failures"] == 0 else ":warning:"
    header = (
        f"{status_emoji} *Deploy Digest* — last {digest['window_minutes']} min\n"
        f"Total: {digest['total']}  "
        f"Success: {digest['successes']}  "
        f"Failure: {digest['failures']}"
    )
    ref_lines = "\n".join(
        f"  • `{ref}`: {count} deploy(s)" for ref, count in digest["refs"].items()
    ) or "  _no deploys_"

    return {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": header}},
            {"type": "section", "text": {"type": "mrkdwn", "text": ref_lines}},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Generated at {digest['generated_at']}",
                    }
                ],
            },
        ]
    }
