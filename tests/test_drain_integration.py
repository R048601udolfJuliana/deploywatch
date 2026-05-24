"""Integration tests for DeployDrain used alongside runner.run_script."""

from __future__ import annotations

import os
import stat
import tempfile
import threading
import time

import pytest

from drain import DeployDrain, DrainTimeout
from runner import run_script


@pytest.fixture()
def slow_script():
    """A script that sleeps briefly so we can observe in-flight state."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False
    ) as fh:
        fh.write("#!/bin/sh\nsleep 0.1\nexit 0\n")
        path = fh.name
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    yield path
    os.unlink(path)


@pytest.fixture()
def fast_failing_script():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False
    ) as fh:
        fh.write("#!/bin/sh\nexit 1\n")
        path = fh.name
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    yield path
    os.unlink(path)


def _deploy(drain: DeployDrain, script: str) -> None:
    with drain:
        run_script(script, ref="refs/heads/main", repo="test/repo")


def test_drain_blocks_until_deploy_finishes(slow_script):
    d = DeployDrain(timeout=5)
    t = threading.Thread(target=_deploy, args=(d, slow_script), daemon=True)
    t.start()
    time.sleep(0.02)  # let the thread acquire
    assert d.in_flight == 1
    d.drain(timeout=5)
    assert d.in_flight == 0


def test_multiple_concurrent_deploys_all_tracked(slow_script):
    d = DeployDrain(timeout=5)
    threads = [
        threading.Thread(target=_deploy, args=(d, slow_script), daemon=True)
        for _ in range(3)
    ]
    for t in threads:
        t.start()
    time.sleep(0.02)
    assert d.in_flight == 3
    d.drain(timeout=5)
    assert d.in_flight == 0


def test_failed_deploy_still_releases(fast_failing_script):
    d = DeployDrain(timeout=5)
    _deploy(d, fast_failing_script)
    assert d.in_flight == 0


def test_no_new_deploys_accepted_after_drain(slow_script):
    d = DeployDrain(timeout=5)
    d.drain()
    with pytest.raises(RuntimeError, match="draining"):
        d.acquire()
