"""Package logger.

pcsf never configures the root logger. It logs to
``logging.getLogger("pcsf")``, which carries a ``NullHandler``, so
that applications decide where messages go. For interactive use,
:func:`enable_console_logging` prints them.
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
        Module name, usually ``__name__``. Names outside the package
        are attached under ``pcsf``.

    Returns
    -------
    logging.Logger
        ``pcsf`` itself when *name* is empty, otherwise a child.

    Examples
    --------
    >>> from pcsf._logging import get_logger
    >>> get_logger("pcsf.core").name, get_logger("plugin").name
    ('pcsf.core', 'pcsf.plugin')
    """
    if not name:
        return logging.getLogger(_ROOT)
    if name == _ROOT or name.startswith(_ROOT + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT}.{name}")


def enable_console_logging(level: int | str = logging.INFO) -> None:
    """Send pcsf log messages to standard error.

    Parameters
    ----------
    level : int or str, default logging.INFO
        Level set on the ``pcsf`` logger.

    Notes
    -----
    A stream handler is added only once, however often the function
    is called; later calls only change the level. This modifies
    global logging state and is meant for scripts and notebooks, not
    for libraries.
    """
    logger = logging.getLogger(_ROOT)
    has_stream = any(
        isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.NullHandler)
        for h in logger.handlers
    )
    if not has_stream:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(level)
