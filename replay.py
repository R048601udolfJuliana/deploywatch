"""Replay — re-run the most recent audit entries through the script runner."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from audit import AuditEntry, recent
from runner import RunResult, run_script

log = logging.getLogger(__name__)


@dataclass
class ReplayResult:
    entry: AuditEntry
    run: Optional[RunResult]
    skipped: bool = False
    skip_reason: str = ""

    @property
    def ok(self) -> bool:
        if self.skipped:
            return False
        return self.run is not None and self.run.returncode == 0


def replay_recent(
    script: str,
    *,
    limit: int = 5,
    dry_run: bool = False,
) -> List[ReplayResult]:
    """Fetch up to *limit* recent audit entries and re-run *script* for each.

    When *dry_run* is True the script is not executed; entries are marked
    skipped instead so callers can preview what would happen.
    """
    entries = recent(limit=limit)
    results: List[ReplayResult] = []

    for entry in entries:
        if dry_run:
            log.info("dry-run: would replay entry %s", entry.event_id)
            results.append(
                ReplayResult(entry=entry, run=None, skipped=True, skip_reason="dry_run")
            )
            continue

        log.info("replaying entry %s via %s", entry.event_id, script)
        run = run_script(script, env={"REPLAY_EVENT_ID": entry.event_id,
                                      "REPLAY_REF": entry.ref or ""})
        results.append(ReplayResult(entry=entry, run=run))

    return results


def summary(results: List[ReplayResult]) -> str:
    """Return a one-line human-readable summary of replay results."""
    total = len(results)
    ok = sum(1 for r in results if r.ok)
    skipped = sum(1 for r in results if r.skipped)
    failed = total - ok - skipped
    return f"replayed {total}: {ok} ok, {failed} failed, {skipped} skipped"
