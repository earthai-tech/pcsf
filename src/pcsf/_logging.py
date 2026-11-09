"""Package logger.

pcsf never configures the root logger. It logs to ``logging.getLogger("pcsf")``
with a ``NullHandler``, so applications decide where messages go. During
development, :func:`enable_console_logging` prints them.
"""

from __future__ import annotations

import logging

__all__ = ["enable_console_logging", "get_logger"]

_ROOT = "pcsf"
logging.getLogger(_ROOT).addHandler(logging.NullHandler())


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the package logger or one of its children.

    Parameters
    ----------
    name : str, optional
        Module name, usually ``__name__``. Names outside the package are
        attached under ``pcsf``.
    """
    if not name:
        return logging.getLogger(_ROOT)
    if name == _ROOT or name.startswith(_ROOT + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT}.{name}")


def enable_console_logging(level: int | str = logging.INFO) -> None:
    """Send pcsf log messages to the console (for interactive use)."""
    logger = logging.getLogger(_ROOT)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.NullHandler)
               for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)
