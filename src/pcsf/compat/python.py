"""Python-version differences."""

from __future__ import annotations

import sys
from importlib import metadata as _metadata

__all__ = ["PY310", "entry_points"]

PY310 = sys.version_info >= (3, 10)


def entry_points(group: str) -> list:
    """Entry points of *group*, on every supported Python version.

    Python 3.9 returns a dict from ``importlib.metadata.entry_points()``;
    3.10+ accepts the ``group`` keyword.
    """
    try:
        return list(_metadata.entry_points(group=group))
    except TypeError:  # Python 3.9
        return list(_metadata.entry_points().get(group, []))
