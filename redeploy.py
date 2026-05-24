"""redeploy.py — Re-run the deploy script for a specific git ref."""
from __future__ import annotations

import dataclasses
from typing import Optional

from audit import AuditEntry, recent
from runner import RunResult, run_script


@dataclasses.dataclass(frozen=True)
class RedeployResult:
    ref: str
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
            return f"redeploy skipped ({self.skip_reason})"
        if self.run is None:
            return "redeploy failed: no run result"
        status = "succeeded" if self.ok else "failed"
        return f"redeploy of {self.ref} {status} (exit {self.run.returncode})"


def _find_entry(ref: str, limit: int = 50) -> Optional[AuditEntry]:
    """Return the most recent audit entry for *ref*, or None."""
    for entry in recent(limit):
        if entry.ref == ref:
            return entry
    return None


def redeploy(ref: str, script: str, timeout: int = 60) -> RedeployResult:
    """Re-run *script* for *ref* if a prior deployment exists in the audit log."""
    entry = _find_entry(ref)
    if entry is None:
        return RedeployResult(
            ref=ref,
            run=None,
            skipped=True,
            skip_reason=f"no prior deployment found for ref '{ref}'",
        )

    run = run_script(script, ref=ref, timeout=timeout)
    return RedeployResult(ref=ref, run=run)
