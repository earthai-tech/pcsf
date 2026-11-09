"""NumPy-version differences."""

from __future__ import annotations

import numpy as np

__all__ = ["NUMPY2", "copy_if_needed", "trapezoid"]

NUMPY2 = int(np.__version__.split(".")[0]) >= 2

#: value of ``copy=`` meaning "copy only if needed" (``None`` in NumPy 2, ``False`` before)
copy_if_needed = None if NUMPY2 else False

trapezoid = getattr(np, "trapezoid", None) or np.trapz  # renamed in NumPy 2.0
