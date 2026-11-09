"""h5py-version differences: strings and attributes."""

from __future__ import annotations

from typing import Any

import h5py
import numpy as np

__all__ = ["decode", "string_dtype"]


def string_dtype():
    """Variable-length UTF-8 string dtype."""
    return h5py.string_dtype(encoding="utf-8")


def decode(value: Any) -> Any:
    """Return ``str`` for bytes or 0-d string values read from HDF5.

    h5py 3 returns ``bytes`` for some string datasets and attributes and
    ``str`` for others, depending on how they were written.
    """
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, np.ndarray) and value.dtype.kind in "SO" and value.ndim == 0:
        return decode(value[()])
    if isinstance(value, np.bytes_):
        return value.decode("utf-8")
    return value
