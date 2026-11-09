"""Array conversion and shape checks."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..exceptions import GeometryError

__all__ = ["as_float_array", "check_shape", "optional_float_array"]


def as_float_array(
    value: Any, *, ndim: int | None = None, name: str = "array"
) -> np.ndarray:
    """Convert to a float array, checking the number of dimensions.

    Parameters
    ----------
    value : array_like
        Input values.
    ndim : int, optional
        Required number of dimensions; not checked when ``None``.
    name : str, default "array"
        Name used in the error message.

    Returns
    -------
    ndarray of float64
        ``np.asarray(value, dtype=float)``; no copy when *value* is
        already a float64 array.

    Raises
    ------
    GeometryError
        If *ndim* is given and does not match.
    ValueError
        If *value* cannot be converted to float.

    Examples
    --------
    >>> from pcsf.utils.arrays import as_float_array
    >>> as_float_array([1, 2], ndim=1).dtype
    dtype('float64')
    >>> as_float_array([1, 2], ndim=2, name="x")
    Traceback (most recent call last):
    ...
    pcsf.exceptions.GeometryError: x must be 2-D, got shape (2,)
    """
    arr = np.asarray(value, dtype=float)
    if ndim is not None and arr.ndim != ndim:
        raise GeometryError(
            f"{name} must be {ndim}-D, got shape {arr.shape}"
        )
    return arr


def optional_float_array(value: Any) -> np.ndarray | None:
    """Convert to a float array, keeping ``None`` as ``None``.

    Parameters
    ----------
    value : array_like or None
        Input values.

    Returns
    -------
    ndarray of float64 or None
        Converted array, or ``None``.

    Examples
    --------
    >>> from pcsf.utils.arrays import optional_float_array
    >>> optional_float_array(None) is None
    True
    """
    return None if value is None else np.asarray(value, dtype=float)


def check_shape(
    arr: np.ndarray,
    expected: tuple[int, ...],
    *,
    name: str = "array",
) -> None:
    """Check that an array has the expected shape.

    Parameters
    ----------
    arr : ndarray
        Array to check.
    expected : tuple of int
        Required shape.
    name : str, default "array"
        Name used in the error message.

    Raises
    ------
    GeometryError
        If ``arr.shape != expected``.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.utils.arrays import check_shape
    >>> check_shape(np.zeros((2, 3)), (2, 3))
    >>> check_shape(np.zeros(2), (3,), name="rho")
    Traceback (most recent call last):
    ...
    pcsf.exceptions.GeometryError: rho has shape (2,), expected (3,)
    """
    if tuple(arr.shape) != tuple(expected):
        raise GeometryError(
            f"{name} has shape {arr.shape}, expected {expected}"
        )
