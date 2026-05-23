import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest

from webhook import make_handler, run_script, verify_signature


SECRET = "test-secret"


def _sign(body: bytes, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _make_config(secret=SECRET, script="./deploy.sh", slack_url=None):
    cfg = MagicMock()
    cfg.webhook_secret = secret
    cfg.deploy_script = script
    cfg.slack_webhook_url = slack_url
    return cfg


def _fake_request(handler_class, path, body: bytes, headers: dict):
    """Simulate a POST request using the handler directly."""
    from io import BytesIO

    request = MagicMock()
    request.makefile.return_value = BytesIO(b"")
    client_address = ("127.0.0.1", 9999)
    server = MagicMock()

    handler = handler_class.__new__(handler_class)
    handler.path = path
    handler.headers = headers
    handler.rfile = BytesIO(body)
    handler.wfile = BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


# --- verify_signature ---

def test_verify_signature_valid():
    body = b'{"ref": "refs/heads/main"}'
    assert verify_signature(body, SECRET, _sign(body)) is True


def test_verify_signature_invalid():
    body = b'{"ref": "refs/heads/main"}'
    assert verify_signature(body, SECRET, "sha256=badhash") is False


def test_verify_signature_missing_header():
    assert verify_signature(b"data", SECRET, "") is False


def test_verify_signature_no_prefix():
    assert verify_signature(b"data", SECRET, "abc123") is False


# --- run_script ---

def test_run_script_success():
    payload = {"ref": "refs/heads/main", "repository": {"full_name": "org/repo"}}
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="deployed", stderr="")
        ok, out = run_script("./deploy.sh", payload)
    assert ok is True
    assert out == "deployed"


def test_run_script_failure():
    payload = {"ref": "refs/heads/main", "repository": {"full_name": "org/repo"}}
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error!")
        ok, out = run_script("./deploy.sh", payload)
    assert ok is False
    assert out == "error!"


def test_run_script_not_found():
    payload = {"ref": "refs/heads/main", "repository": {"full_name": "org/repo"}}
    with patch("subprocess.run", side_effect=FileNotFoundError):
        ok, out = run_script("./missing.sh", payload)
    assert ok is False
    assert "not found" in out


# --- WebhookHandler via make_handler ---

def test_handler_wrong_path():
    cfg = _make_config()
    HandlerClass = make_handler(cfg)
    body = b'{"ref": "refs/heads/main"}'
    handler = _fake_request(HandlerClass, "/other", body, {})
    handler.do_POST()
    handler.send_response.assert_called_with(404)


def test_handler_bad_signature():
    cfg = _make_config()
    HandlerClass = make_handler(cfg)
    body = b'{"ref": "refs/heads/main"}'
    headers = {"Content-Length": str(len(body)), "X-Hub-Signature-256": "sha256=bad", "X-GitHub-Event": "push"}
    handler = _fake_request(HandlerClass, "/webhook", body, headers)
    handler.do_POST()
    handler.send_response.assert_called_with(401)


def test_handler_non_push_event_ignored():
    cfg = _make_config()
    HandlerClass = make_handler(cfg)
    body = b'{"action": "opened"}'
    headers = {
        "Content-Length": str(len(body)),
        "X-Hub-Signature-256": _sign(body),
        "X-GitHub-Event": "pull_request",
    }
    handler = _fake_request(HandlerClass, "/webhook", body, headers)
    handler.do_POST()
    handler.send_response.assert_called_with(200)
