"""Tests for banner.py."""

import io
import sys
from unittest.mock import patch

import banner as bn


# ---------------------------------------------------------------------------
# version()
# ---------------------------------------------------------------------------

def test_version_returns_string():
    assert isinstance(bn.version(), str)


def test_version_matches_module_constant():
    assert bn.version() == bn.__version__


# ---------------------------------------------------------------------------
# build_info()
# ---------------------------------------------------------------------------

def test_build_info_has_required_keys():
    info = bn.build_info()
    assert "version" in info
    assert "python" in info
    assert "started_at" in info


def test_build_info_version_matches():
    assert bn.build_info()["version"] == bn.__version__


def test_build_info_python_matches_runtime():
    expected = sys.version.split()[0]
    assert bn.build_info()["python"] == expected


def test_build_info_started_at_is_utc_iso():
    started_at = bn.build_info()["started_at"]
    # Should end with +00:00 (timezone-aware ISO-8601)
    assert "+00:00" in started_at


# ---------------------------------------------------------------------------
# print_banner()
# ---------------------------------------------------------------------------

def test_print_banner_writes_to_file():
    buf = io.StringIO()
    bn.print_banner(8000, 8001, file=buf)
    output = buf.getvalue()
    assert len(output) > 0


def test_print_banner_contains_ports():
    buf = io.StringIO()
    bn.print_banner(9000, 9001, file=buf)
    output = buf.getvalue()
    assert "9000" in output
    assert "9001" in output


def test_print_banner_contains_version():
    buf = io.StringIO()
    bn.print_banner(8000, 8001, file=buf)
    assert bn.__version__ in buf.getvalue()


def test_print_banner_defaults_to_stdout(capsys):
    bn.print_banner(8080, 8081)
    captured = capsys.readouterr()
    assert "8080" in captured.out
    assert "8081" in captured.out


def test_print_banner_contains_logo_text():
    buf = io.StringIO()
    bn.print_banner(8000, 8001, file=buf)
    # The logo contains the product name fragment
    assert "Watch" in buf.getvalue() or "watch" in buf.getvalue()
