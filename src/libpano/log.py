"""Logging configuration for the application."""

import logging

from .const import DT_STYLE_FOLDER, DT_STYLES, LOG_FOLDER

# Configure logging
LOG_FILE = LOG_FOLDER / "pano.log"
LOG_FORMAT = "%(asctime)s - %(name)-20s - %(levelname)-8s - %(message)s"


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for a given module name."""
    return logging.getLogger(name)


logger = get_logger(__name__)

logger.info(f"Logging to: {LOG_FILE}")
logger.info(f"Darktable style folder set to: {DT_STYLE_FOLDER}")
logger.info(f"Darktable styles available: {DT_STYLES}")
