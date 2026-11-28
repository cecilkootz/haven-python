"""Logging configuration for Haven Lighting.

A library must not configure logging for the application that imports it:
the package only attaches a NullHandler (see ``havenlighting/__init__.py``)
and leaves levels and handlers to the application, e.g. Home Assistant's
``logger:`` integration. ``setup_logging`` is an opt-in convenience for
scripts such as ``examples/demo.py``.
"""

import logging
from typing import Optional

_HANDLER_MARKER = "_havenlighting_handler"


def setup_logging(level: int = logging.INFO,
                  log_file: Optional[str] = None) -> None:
    """
    Configure console (and optionally file) logging for havenlighting.

    Safe to call repeatedly: handlers installed by an earlier call are
    replaced rather than stacked, so log lines are never duplicated.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path for logging output
    """
    logger = logging.getLogger("havenlighting")
    logger.setLevel(level)

    for handler in list(logger.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            logger.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    for handler in handlers:
        handler.setFormatter(formatter)
        setattr(handler, _HANDLER_MARKER, True)
        logger.addHandler(handler)
