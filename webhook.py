import hashlib
import hmac
import json
import logging
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import Config
from notifier import send_notification

logger = logging.getLogger(__name__)


def verify_signature(payload_body: bytes, secret: str, signature_header: str) -> bool:
    """Verify the GitHub HMAC-SHA256 webhook signature."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def run_script(script_path: str, payload: dict) -> tuple[bool, str]:
    """Execute the deploy script, passing the branch name as an argument."""
    branch = payload.get("ref", "").replace("refs/heads/", "")
    repo = payload.get("repository", {}).get("full_name", "unknown")
    try:
        result = subprocess.run(
            [script_path, branch, repo],
            capture_output=True,
            text=True,
            timeout=120,
        )
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        return success, output.strip()
    except FileNotFoundError:
        return False, f"Script not found: {script_path}"
    except subprocess.TimeoutExpired:
        return False, "Script execution timed out after 120s"


def make_handler(config: Config):
    """Return a request handler class bound to the given config."""

    class WebhookHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002
            logger.info("%s - %s", self.address_string(), format % args)

        def do_POST(self):
            if self.path != "/webhook":
                self._respond(404, "Not Found")
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            sig = self.headers.get("X-Hub-Signature-256", "")
            if not verify_signature(body, config.webhook_secret, sig):
                logger.warning("Invalid webhook signature")
                self._respond(401, "Unauthorized")
                return

            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self._respond(400, "Bad Request")
                return

            event = self.headers.get("X-GitHub-Event", "")
            if event != "push":
                self._respond(200, "Ignored")
                return

            success, output = run_script(config.deploy_script, payload)
            branch = payload.get("ref", "").replace("refs/heads/", "")
            repo = payload.get("repository", {}).get("full_name", "unknown")
            send_notification(config, repo=repo, branch=branch, success=success, output=output)

            status = 200 if success else 500
            self._respond(status, "OK" if success else "Script failed")

        def _respond(self, code: int, message: str):
            self.send_response(code)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(message.encode())

    return WebhookHandler


def start_server(config: Config):
    handler = make_handler(config)
    server = HTTPServer((config.host, config.port), handler)
    logger.info("deploywatch listening on %s:%s", config.host, config.port)
    server.serve_forever()
