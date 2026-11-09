"""Differences between NumPy 1.x and 2.x.

Attributes
----------
NUMPY2 : bool
    True on NumPy 2.0 or later.
copy_if_needed : bool or None
    Value of the ``copy=`` argument that copies only when needed:
    ``None`` on NumPy 2, ``False`` before.
trapezoid : callable
    ``numpy.trapezoid`` (NumPy 2), or ``numpy.trapz`` before it was
    renamed.

Examples
--------
>>> from pcsf.compat.numpy import trapezoid
>>> float(trapezoid([0.0, 1.0, 2.0]))
2.0
"""

from __future__ import annotations

import numpy as np

__all__ = ["NUMPY2", "copy_if_needed", "trapezoid"]

NUMPY2 = int(np.__version__.split(".")[0]) >= 2

copy_if_needed = None if NUMPY2 else False

# Renamed in NumPy 2.0; np.trapz is deprecated there.
trapezoid = getattr(np, "trapezoid", None) or np.trapz  # noqa: NPY201
