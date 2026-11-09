"""Differences between Python 3.9 and 3.10+.

Attributes
----------
PY310 : bool
    True on Python 3.10 or later.
"""

from __future__ import annotations

import sys
from importlib import metadata as _metadata

__all__ = ["PY310", "entry_points"]

PY310 = sys.version_info >= (3, 10)


def entry_points(group: str) -> list:
    """Entry points of a group on every supported Python version.

    Parameters
    ----------
    group : str
        Entry-point group, such as ``"pcsf.encodings"``.

    Returns
    -------
    list of importlib.metadata.EntryPoint
        Entry points of installed distributions; empty when none.

    Notes
    -----
    Python 3.9 returns a dictionary from
    ``importlib.metadata.entry_points()``; 3.10 and later accept the
    ``group`` keyword.

    Examples
    --------
    >>> from pcsf.compat.python import entry_points
    >>> entry_points("pcsf.no_such_group")
    []
    """
    try:
        return list(_metadata.entry_points(group=group))
    except TypeError:  # Python 3.9
        return list(_metadata.entry_points().get(group, []))
