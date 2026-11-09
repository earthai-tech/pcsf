"""Text helpers."""

from __future__ import annotations

import math

__all__ = ["format_float"]


def format_float(value: float) -> str:
    """Shortest decimal string that reads back as the same double.

    Parameters
    ----------
    value : float
        Value to format.

    Returns
    -------
    str
        Decimal representation; ``"nan"``, ``"inf"`` or ``"-inf"``
        for non-finite values.

    Notes
    -----
    Python's ``repr`` of a float is the shortest string that converts
    back to the same IEEE 754 double, which makes PCSM text lossless.

    Examples
    --------
    >>> from pcsf.utils.text import format_float
    >>> format_float(0.1), format_float(1e-300), format_float(-1e999)
    ('0.1', '1e-300', '-inf')
    >>> float(format_float(1 / 3)) == 1 / 3
    True
    """
    v = float(value)
    if math.isnan(v):
        return "nan"
    if math.isinf(v):
        return "inf" if v > 0 else "-inf"
    return repr(v)
