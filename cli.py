"""Entry-point for the deploywatch server."""

import argparse
import sys
from http.server import HTTPServer
from threading import Thread

from config import load_config, validate
from healthcheck import make_health_handler
from logger import configure_root, get_logger
from webhook import make_handler


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="deploywatch",
        description="Webhook server that triggers shell scripts on GitHub push events.",
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        default=None,
        help="Path to .env config file (defaults to environment variables).",
    )
    parser.add_argument(
        "--health-port",
        type=int,
        default=8081,
        help="Port for the /health endpoint (default: 8081).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO).",
    )
    return parser.parse_args(argv)


def _start_health_server(port: int, config_valid: bool) -> Thread:
    """Start the health-check HTTP server in a daemon thread."""
    handler = make_health_handler(config_valid=config_valid)
    server = HTTPServer(("0.0.0.0", port), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


def main(argv=None) -> int:
    args = _parse_args(argv)
    configure_root(level=args.log_level)
    log = get_logger("cli")

    cfg = load_config(path=args.config)
    try:
        validate(cfg)
        config_valid = True
    except ValueError as exc:
        log.error("Invalid configuration", extra={"error": str(exc)})
        config_valid = False

    _start_health_server(args.health_port, config_valid)
    log.info("Health server started", extra={"port": args.health_port})

    if not config_valid:
        log.error("Aborting: fix configuration errors before starting webhook server.")
        return 1

    handler_class = make_handler(cfg)
    server = HTTPServer(("0.0.0.0", cfg.port), handler_class)
    log.info("Webhook server started", extra={"port": cfg.port})

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
