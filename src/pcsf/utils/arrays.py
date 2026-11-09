"""Array helpers."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..exceptions import GeometryError

__all__ = ["as_float_array", "check_shape", "optional_float_array"]


def as_float_array(value: Any, *, ndim: int | None = None, name: str = "array") -> np.ndarray:
    """``np.asarray(value, float)``, checking the number of dimensions."""
    arr = np.asarray(value, dtype=float)
    if ndim is not None and arr.ndim != ndim:
        raise GeometryError(f"{name} must be {ndim}-D, got shape {arr.shape}")
    return arr


def optional_float_array(value: Any) -> np.ndarray | None:
    """Like :func:`as_float_array`, but ``None`` stays ``None``."""
    return None if value is None else np.asarray(value, dtype=float)


def check_shape(arr: np.ndarray, expected: tuple[int, ...], *, name: str = "array") -> None:
    """Raise :class:`GeometryError` if ``arr.shape != expected``."""
    if tuple(arr.shape) != tuple(expected):
        raise GeometryError(f"{name} has shape {arr.shape}, expected {expected}")
