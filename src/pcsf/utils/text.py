"""Text helpers."""

from __future__ import annotations

import math

__all__ = ["format_float"]


def format_float(value: float) -> str:
    """Shortest decimal string that converts back to the same IEEE 754 double.

    Python's ``repr`` already has this property (Steele and White, 1990);
    non-finite values are written as ``nan``, ``inf`` and ``-inf``.
    """
    v = float(value)
    if math.isnan(v):
        return "nan"
    if math.isinf(v):
        return "inf" if v > 0 else "-inf"
    return repr(v)
