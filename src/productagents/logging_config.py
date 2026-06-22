"""File-based logging setup for the application.

The Textual TUI owns the terminal, so logging must never write to stdout or
stderr — that would corrupt the rendered screen. `configure_logging()` installs
a single rotating *file* handler on the `productagents` logger and turns off
propagation so records never reach root's stderr `lastResort` handler. Every
module logs through `logging.getLogger(__name__)` (a `productagents.*` child),
whose records are handled by that one file handler.

Configured by env:
- `PRODUCTAGENTS_LOG_FILE`  — log file path (default `productagents.log`).
- `PRODUCTAGENTS_LOG_LEVEL` — level name (default `INFO`; invalid → `INFO`).
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

DEFAULT_LOG_FILE = "productagents.log"
DEFAULT_LEVEL = "INFO"

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging() -> Path:
    """Install a file-only rotating handler on the `productagents` logger.

    Idempotent: re-configuring removes the handler a previous call installed and
    re-points to the (possibly new) log file, so there is never more than one of
    our handlers. Returns the resolved log-file path.
    """
    log_file = Path(os.environ.get("PRODUCTAGENTS_LOG_FILE", DEFAULT_LOG_FILE))
    level_name = os.environ.get("PRODUCTAGENTS_LOG_LEVEL", DEFAULT_LEVEL).upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        level = logging.INFO

    logger = logging.getLogger("productagents")
    logger.setLevel(level)
    logger.propagate = False

    for handler in list(logger.handlers):
        if getattr(handler, "_productagents_handler", False):
            logger.removeHandler(handler)
            handler.close()

    handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    cast_handler: Any = handler
    cast_handler._productagents_handler = True
    handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(handler)

    return log_file
