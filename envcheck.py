"""envcheck.py – Validate required environment variables at startup."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EnvVar:
    name: str
    required: bool = True
    default: Optional[str] = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "required": self.required,
            "present": self.name in os.environ,
            "has_default": self.default is not None,
            "description": self.description,
        }


@dataclass
class EnvReport:
    vars: List[EnvVar] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return len(self.missing) == 0

    def to_dict(self) -> dict:
        return {
            "all_ok": self.all_ok,
            "missing": self.missing,
            "vars": [v.to_dict() for v in self.vars],
        }


# Variables that deploywatch depends on.
_REQUIRED_VARS: List[EnvVar] = [
    EnvVar("WEBHOOK_SECRET", required=True, description="HMAC secret for GitHub webhooks"),
    EnvVar("DEPLOY_SCRIPT", required=True, description="Path to the deploy shell script"),
    EnvVar("SLACK_WEBHOOK_URL", required=False, description="Slack incoming webhook URL"),
    EnvVar("HEALTH_PORT", required=False, default="9090", description="Port for the health endpoint"),
    EnvVar("LOG_LEVEL", required=False, default="INFO", description="Logging verbosity"),
]


def check(extra: Optional[List[EnvVar]] = None) -> EnvReport:
    """Run environment checks and return an EnvReport."""
    vars_to_check = list(_REQUIRED_VARS)
    if extra:
        vars_to_check.extend(extra)

    missing: List[str] = []
    for ev in vars_to_check:
        if ev.required and ev.name not in os.environ and ev.default is None:
            missing.append(ev.name)

    return EnvReport(vars=vars_to_check, missing=missing)


def assert_env(extra: Optional[List[EnvVar]] = None) -> None:
    """Raise EnvironmentError if any required variable is absent."""
    report = check(extra)
    if not report.all_ok:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(report.missing)}"
        )
