"""banner.py – startup banner and version info for deploywatch."""

import sys
from datetime import datetime, timezone

__version__ = "0.1.0"

_LOGO = """
 ____            _             __        __    _       _
|  _ \  ___ _ __| | ___  _   _\ \      / /_ _| |_ ___| |__
| | | |/ _ \ '_ \ |/ _ \| | | \ \ /\ / / _` | __/ __| '_ \
| |_| |  __/ |_) | | (_) | |_| |\ V  V / (_| | || (__| | | |
|____/ \___| .__/|_|\___/ \__, | \_/\_/ \__,_|\__\___|_| |_|
           |_|            |___/
""".strip()


def version() -> str:
    """Return the current deploywatch version string."""
    return __version__


def build_info() -> dict:
    """Return a dict with version and startup timestamp (UTC ISO-8601)."""
    return {
        "version": __version__,
        "python": sys.version.split()[0],
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def print_banner(port: int, health_port: int, *, file=None) -> None:
    """Print the ASCII logo and key startup info to *file* (default stdout)."""
    if file is None:
        file = sys.stdout
    info = build_info()
    lines = [
        _LOGO,
        "",
        f"  version      : {info['version']}",
        f"  python       : {info['python']}",
        f"  started      : {info['started_at']}",
        f"  webhook port : {port}",
        f"  health  port : {health_port}",
        "",
    ]
    print("\n".join(lines), file=file)
