"""rollback.py – re-run the last successful deploy for a given ref."""
from __future__ import annotations

import dataclasses
from typing import Optional

from audit import AuditEntry, recent
from runner import RunResult, run_script


@dataclasses.dataclass
class RollbackResult:
    ref: str
    entry: Optional[AuditEntry]
    run: Optional[RunResult]
    skipped: bool = False
    skip_reason: str = ""

    @property
    def ok(self) -> bool:
        if self.skipped:
            return False
        return self.run is not None and self.run.returncode == 0

    def summary(self) -> str:
        if self.skipped:
            return f"rollback skipped ({self.skip_reason})"
        if self.run is None:
            return "rollback failed: no run result"
        return f"rollback {'succeeded' if self.ok else 'failed'} for {self.ref} (rc={self.run.returncode})"


def _last_success(ref: str, limit: int = 100) -> Optional[AuditEntry]:
    """Return the most recent successful audit entry for *ref*."""
    for entry in recent(limit):
        if entry.ref == ref and entry.success:
            return entry
    return None


def rollback(ref: str, script: str, timeout: int = 60) -> RollbackResult:
    """Re-execute *script* using metadata from the last good deploy of *ref*."""
    entry = _last_success(ref)
    if entry is None:
        return RollbackResult(
            ref=ref,
            entry=None,
            run=None,
            skipped=True,
            skip_reason=f"no successful deploy found for ref '{ref}'",
        )

    run = run_script(script, ref=entry.ref, sha=entry.sha, timeout=timeout)
    return RollbackResult(ref=ref, entry=entry, run=run)
