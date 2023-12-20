"""Run subprocesses silently."""

import subprocess as sp
from pathlib import Path

from .log import get_logger

logger = get_logger(__name__)

def run(cmd: list[str | Path], allow_error: bool = False):
    """Run a command with subprocess."""
    cmdstr = [str(c) for c in cmd]
    try:
        logger.info(f"Running command: {' '.join(cmdstr)}")
        result = sp.run(cmdstr, capture_output=True, text=True)

        if result.stdout:
            logger.info(f"Command output: {result.stdout.strip()}")
        if result.stderr:
            logger.warning(f"Command error: {result.stderr.strip()}")
    except Exception as e:
        logger.error(f"Failed to run command: {e}")
        if not allow_error:
            raise
