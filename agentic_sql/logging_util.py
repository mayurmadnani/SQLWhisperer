"""Central logging configuration for the Agentic SQL demo."""
from __future__ import annotations

import logging
import os

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

_handler = logging.StreamHandler()
_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
_handler.setFormatter(_formatter)

logger = logging.getLogger("agentic_sql")
if not logger.handlers:
    logger.addHandler(_handler)
logger.setLevel(_LOG_LEVEL)
logger.propagate = False

__all__ = ["logger"]
