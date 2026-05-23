"""Script runner module for deploywatch.

Handles execution of shell scripts triggered by GitHub push events,
capturing output and reporting results.
"""

import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Result of a script execution."""

    script: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    error: Optional[str] = None

    @property
    def summary(self) -> str:
        status = "succeeded" if self.success else "failed"
        return (
            f"Script `{self.script}` {status} "
            f"(exit {self.exit_code}, {self.duration:.2f}s)"
        )


def run_script(script_path: str, timeout: int = 60) -> RunResult:
    """Execute a shell script and return a RunResult.

    Args:
        script_path: Absolute or relative path to the script.
        timeout: Maximum seconds to wait before killing the process.

    Returns:
        RunResult with execution details.
    """
    path = Path(script_path)
    script_name = path.name

    if not path.exists():
        logger.error("Script not found: %s", script_path)
        return RunResult(
            script=script_name,
            success=False,
            exit_code=-1,
            stdout="",
            stderr="",
            duration=0.0,
            error=f"Script not found: {script_path}",
        )

    if not path.stat().st_mode & 0o111:
        logger.error("Script is not executable: %s", script_path)
        return RunResult(
            script=script_name,
            success=False,
            exit_code=-1,
            stdout="",
            stderr="",
            duration=0.0,
            error=f"Script is not executable: {script_path}",
        )

    logger.info("Running script: %s", script_path)
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.monotonic() - start
        success = proc.returncode == 0
        if success:
            logger.info("Script succeeded: %s", script_name)
        else:
            logger.warning("Script failed (exit %d): %s", proc.returncode, script_name)
        return RunResult(
            script=script_name,
            success=success,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration=duration,
        )
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        logger.error("Script timed out after %ds: %s", timeout, script_name)
        return RunResult(
            script=script_name,
            success=False,
            exit_code=-1,
            stdout="",
            stderr="",
            duration=duration,
            error=f"Timed out after {timeout}s",
        )
