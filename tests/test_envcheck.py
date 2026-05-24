"""Tests for envcheck.py"""
from __future__ import annotations

import os
import pytest

import envcheck
from envcheck import EnvVar, EnvReport, check, assert_env


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_env(monkeypatch, **kwargs):
    """Set env vars for the duration of a test."""
    for k, v in kwargs.items():
        monkeypatch.setenv(k, v)


def _clear_required(monkeypatch):
    """Remove all built-in required vars so tests start from a clean slate."""
    for ev in envcheck._REQUIRED_VARS:
        monkeypatch.delenv(ev.name, raising=False)


# ---------------------------------------------------------------------------
# EnvVar.to_dict
# ---------------------------------------------------------------------------

def test_env_var_to_dict_present(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cr3t")
    ev = EnvVar("WEBHOOK_SECRET", required=True)
    d = ev.to_dict()
    assert d["name"] == "WEBHOOK_SECRET"
    assert d["present"] is True
    assert d["required"] is True


def test_env_var_to_dict_absent(monkeypatch):
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    ev = EnvVar("WEBHOOK_SECRET", required=True)
    assert ev.to_dict()["present"] is False


def test_env_var_to_dict_has_default():
    ev = EnvVar("LOG_LEVEL", required=False, default="INFO")
    assert ev.to_dict()["has_default"] is True


# ---------------------------------------------------------------------------
# EnvReport
# ---------------------------------------------------------------------------

def test_report_all_ok_when_no_missing():
    report = EnvReport(vars=[], missing=[])
    assert report.all_ok is True


def test_report_not_ok_when_missing():
    report = EnvReport(vars=[], missing=["WEBHOOK_SECRET"])
    assert report.all_ok is False


def test_report_to_dict_structure():
    ev = EnvVar("DEPLOY_SCRIPT", required=True)
    report = EnvReport(vars=[ev], missing=["DEPLOY_SCRIPT"])
    d = report.to_dict()
    assert "all_ok" in d
    assert "missing" in d
    assert "vars" in d
    assert isinstance(d["vars"], list)


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------

def test_check_passes_when_required_vars_set(monkeypatch):
    _patch_env(monkeypatch, WEBHOOK_SECRET="abc", DEPLOY_SCRIPT="/deploy.sh")
    report = check()
    # May still have missing if other required vars absent; just verify those two
    # are not in missing.
    assert "WEBHOOK_SECRET" not in report.missing
    assert "DEPLOY_SCRIPT" not in report.missing


def test_check_reports_missing_required(monkeypatch):
    _clear_required(monkeypatch)
    report = check()
    assert "WEBHOOK_SECRET" in report.missing
    assert "DEPLOY_SCRIPT" in report.missing


def test_check_optional_vars_not_in_missing(monkeypatch):
    _clear_required(monkeypatch)
    report = check()
    assert "SLACK_WEBHOOK_URL" not in report.missing
    assert "LOG_LEVEL" not in report.missing


def test_check_accepts_extra_vars(monkeypatch):
    _clear_required(monkeypatch)
    extra = [EnvVar("MY_CUSTOM_VAR", required=True)]
    monkeypatch.delenv("MY_CUSTOM_VAR", raising=False)
    report = check(extra=extra)
    assert "MY_CUSTOM_VAR" in report.missing


def test_check_extra_optional_not_missing(monkeypatch):
    _clear_required(monkeypatch)
    extra = [EnvVar("OPTIONAL_EXTRA", required=False)]
    monkeypatch.delenv("OPTIONAL_EXTRA", raising=False)
    report = check(extra=extra)
    assert "OPTIONAL_EXTRA" not in report.missing


# ---------------------------------------------------------------------------
# assert_env()
# ---------------------------------------------------------------------------

def test_assert_env_raises_when_missing(monkeypatch):
    _clear_required(monkeypatch)
    with pytest.raises(EnvironmentError, match="WEBHOOK_SECRET"):
        assert_env()


def test_assert_env_passes_when_all_set(monkeypatch):
    _patch_env(monkeypatch, WEBHOOK_SECRET="s", DEPLOY_SCRIPT="/d.sh")
    # Should not raise (optional vars are fine to be absent)
    assert_env()
