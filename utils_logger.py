"""
EvalForge AI — utils/logger.py
Centralized structured logging. All services import get_logger() from here.
In production, swap the handler for a JSON formatter (e.g. structlog)
and ship to Datadog / CloudWatch.
"""

import logging
import os
import sys
from typing import Optional

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def _configure():
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    root.addHandler(handler)

    # Silence noisy third-party libs
    for lib in ("httpx", "httpcore", "chromadb", "urllib3", "asyncio"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns a configured logger for the given module name.

    Usage:
        from utils.logger import get_logger
        log = get_logger(__name__)
        log.info("Service started.")
    """
    _configure()
    return logging.getLogger(name or "evalforge")
