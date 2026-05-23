import os
import pytest
from config import Config, load_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQUIRED_ENV = {"DW_GITHUB_SECRET": "test-secret"}


def _make_config(**kwargs) -> Config:
    """Convenience: build a Config with required fields pre-filled."""
    defaults = dict(
        github_secret="test-secret",
        host="127.0.0.1",
        port=8080,
        slack_webhook_url=None,
        scripts_dir="./scripts",
        deploy_branch="main",
        script_timeout=120,
    )
    defaults.update(kwargs)
    return Config(**defaults)


# ---------------------------------------------------------------------------
# Default value tests
# ---------------------------------------------------------------------------


def test_defaults_from_env(monkeypatch):
    monkeypatch.setenv("DW_GITHUB_SECRET", "mysecret")
    # Remove optional vars so defaults kick in
    for key in ("DW_HOST", "DW_PORT", "DW_SCRIPTS_DIR", "DW_DEPLOY_BRANCH", "DW_SCRIPT_TIMEOUT"):
        monkeypatch.delenv(key, raising=False)

    cfg = Config()
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 8080
    assert cfg.scripts_dir == "./scripts"
    assert cfg.deploy_branch == "main"
    assert cfg.script_timeout == 120


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("DW_HOST", "127.0.0.1")
    monkeypatch.setenv("DW_PORT", "9000")
    monkeypatch.setenv("DW_GITHUB_SECRET", "s3cr3t")
    monkeypatch.setenv("DW_SLACK_WEBHOOK_URL", "https://hooks.slack.com/xxx")
    monkeypatch.setenv("DW_SCRIPTS_DIR", "/opt/scripts")
    monkeypatch.setenv("DW_DEPLOY_BRANCH", "production")
    monkeypatch.setenv("DW_SCRIPT_TIMEOUT", "60")

    cfg = Config()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9000
    assert cfg.github_secret == "s3cr3t"
    assert cfg.slack_webhook_url == "https://hooks.slack.com/xxx"
    assert cfg.scripts_dir == "/opt/scripts"
    assert cfg.deploy_branch == "production"
    assert cfg.script_timeout == 60


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


def test_validate_raises_without_secret():
    cfg = _make_config(github_secret="")
    with pytest.raises(ValueError, match="DW_GITHUB_SECRET"):
        cfg.validate()


def test_validate_raises_invalid_port():
    cfg = _make_config(port=0)
    with pytest.raises(ValueError, match="DW_PORT"):
        cfg.validate()

    cfg2 = _make_config(port=99999)
    with pytest.raises(ValueError, match="DW_PORT"):
        cfg2.validate()


def test_validate_raises_invalid_timeout():
    cfg = _make_config(script_timeout=0)
    with pytest.raises(ValueError, match="DW_SCRIPT_TIMEOUT"):
        cfg.validate()


def test_load_config_success(monkeypatch):
    monkeypatch.setenv("DW_GITHUB_SECRET", "valid-secret")
    cfg = load_config()
    assert cfg.github_secret == "valid-secret"


def test_load_config_missing_secret(monkeypatch):
    monkeypatch.delenv("DW_GITHUB_SECRET", raising=False)
    with pytest.raises(ValueError):
        load_config()
