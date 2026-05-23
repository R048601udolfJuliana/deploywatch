import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Central configuration for deploywatch loaded from environment variables."""

    # Server settings
    host: str = field(default_factory=lambda: os.getenv("DW_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("DW_PORT", "8080")))

    # GitHub webhook secret used to validate incoming payloads
    github_secret: str = field(default_factory=lambda: os.getenv("DW_GITHUB_SECRET", ""))

    # Slack incoming webhook URL for notifications
    slack_webhook_url: Optional[str] = field(
        default_factory=lambda: os.getenv("DW_SLACK_WEBHOOK_URL")
    )

    # Directory that contains deploy scripts (one per repo, named <repo>.sh)
    scripts_dir: str = field(
        default_factory=lambda: os.getenv("DW_SCRIPTS_DIR", "./scripts")
    )

    # Branch filter — only trigger deploys for this branch (e.g. "main")
    deploy_branch: str = field(
        default_factory=lambda: os.getenv("DW_DEPLOY_BRANCH", "main")
    )

    # Maximum seconds to wait for a deploy script to finish
    script_timeout: int = field(
        default_factory=lambda: int(os.getenv("DW_SCRIPT_TIMEOUT", "120"))
    )

    def validate(self) -> None:
        """Raise ValueError for any missing required settings."""
        if not self.github_secret:
            raise ValueError(
                "DW_GITHUB_SECRET is required. "
                "Set it to the secret configured in your GitHub webhook."
            )
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"DW_PORT must be between 1 and 65535, got {self.port}")
        if self.script_timeout < 1:
            raise ValueError(
                f"DW_SCRIPT_TIMEOUT must be a positive integer, got {self.script_timeout}"
            )


def load_config() -> Config:
    """Create, validate, and return the application configuration."""
    cfg = Config()
    cfg.validate()
    return cfg
