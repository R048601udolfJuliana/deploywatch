"""preflightcheck.py – pre-deploy sanity checks.

Runs a lightweight suite of checks before a deployment is allowed to proceed:
  - deploy lock is not held
  - deploy is not paused
  - circuit breaker is closed for the target ref
  - dependency health is fully OK
  - environment variables required for deployment are present

Usage::

    from preflightcheck import run_preflight, PreflightResult

    result = run_preflight(ref="refs/heads/main")
    if not result.ok:
        raise RuntimeError(result.summary())
"""

from __future__ import annotations

import dataclasses
from typing import List, Optional

import deploylock
import pausecontrol
import circuit as circuit_mod
import depcheck
import envcheck

# ---------------------------------------------------------------------------
# Module-level optional collaborators (injected by configure())
# ---------------------------------------------------------------------------

_circuit_breaker: Optional[circuit_mod.CircuitBreaker] = None


def configure(breaker: Optional[circuit_mod.CircuitBreaker] = None) -> None:
    """Attach a shared CircuitBreaker instance used by run_preflight."""
    global _circuit_breaker
    _circuit_breaker = breaker


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class PreflightResult:
    """Aggregated outcome of all pre-deploy checks."""

    ok: bool
    failures: List[str] = dataclasses.field(default_factory=list)

    def summary(self) -> str:
        """Return a human-readable summary of the preflight result."""
        if self.ok:
            return "preflight: all checks passed"
        joined = "; ".join(self.failures)
        return f"preflight: {len(self.failures)} check(s) failed – {joined}"

    def to_dict(self) -> dict:
        return {"ok": self.ok, "failures": list(self.failures)}


# ---------------------------------------------------------------------------
# Individual check helpers
# ---------------------------------------------------------------------------

def _check_deploy_lock() -> Optional[str]:
    """Return an error string if the global deploy lock is held."""
    try:
        deploylock.check()
        return None
    except deploylock.DeployLockError as exc:
        return str(exc)


def _check_pause(ref: str) -> Optional[str]:
    """Return an error string if deployments are currently paused."""
    try:
        pausecontrol.check(ref)
        return None
    except pausecontrol.DeployPaused as exc:
        return str(exc)


def _check_circuit(ref: str) -> Optional[str]:
    """Return an error string if the circuit breaker is open for *ref*."""
    if _circuit_breaker is None:
        return None
    try:
        _circuit_breaker.check(ref)
        return None
    except circuit_mod.CircuitOpenError as exc:
        return str(exc)


def _check_dependencies() -> Optional[str]:
    """Return an error string if any registered dependency is unhealthy."""
    checks = depcheck._get_checks()  # reuse the module-level registry
    if not checks:
        return None
    report = depcheck.run_checks(checks)
    if not report.all_ok():
        bad = [s.name for s in report.statuses if not s.ok]
        return f"unhealthy dependencies: {', '.join(bad)}"
    return None


def _check_env() -> Optional[str]:
    """Return an error string if any required environment variable is absent."""
    report = envcheck.check_required()
    if not report.all_ok():
        missing = [v.name for v in report.vars if not v.present]
        return f"missing env vars: {', '.join(missing)}"
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_preflight(ref: str = "") -> PreflightResult:
    """Execute all pre-deploy checks and return an aggregated result.

    Parameters
    ----------
    ref:
        The git ref being deployed (e.g. ``"refs/heads/main"``).  Used by
        checks that are ref-scoped (circuit breaker, pause control).
    """
    failures: List[str] = []

    for error in (
        _check_deploy_lock(),
        _check_pause(ref),
        _check_circuit(ref),
        _check_dependencies(),
        _check_env(),
    ):
        if error is not None:
            failures.append(error)

    return PreflightResult(ok=len(failures) == 0, failures=failures)
