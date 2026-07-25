"""Logging configuration utility."""

from __future__ import annotations

import logging
from typing import Literal


def configure_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
) -> None:
    """Configure root logging with a consistent console format."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    root_logger.addHandler(stream_handler)
    root_logger.setLevel(level)

    logging.debug(
        f"Logging initialized at level {logging.getLevelName(root_logger.level)}"
    )
