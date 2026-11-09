"""String and attribute handling across h5py versions."""

from __future__ import annotations

from typing import Any

import h5py
import numpy as np

__all__ = ["decode", "string_dtype"]


def string_dtype() -> np.dtype:
    """Variable-length UTF-8 string dtype for HDF5 datasets.

    Returns
    -------
    numpy.dtype
        The h5py special dtype.

    Examples
    --------
    >>> from pcsf.compat.h5py import string_dtype
    >>> string_dtype().kind
    'O'
    """
    return h5py.string_dtype(encoding="utf-8")


def decode(value: Any) -> Any:
    """Return ``str`` for bytes or 0-d string values read from HDF5.

    Parameters
    ----------
    value : object
        Value of an attribute or dataset as returned by h5py.

    Returns
    -------
    object
        ``str`` for ``bytes``, ``numpy.bytes_`` and 0-d string
        arrays (decoded as UTF-8); any other value unchanged.

    Raises
    ------
    UnicodeDecodeError
        If bytes are not valid UTF-8.

    Notes
    -----
    h5py 3 returns ``bytes`` for some string datasets and attributes
    and ``str`` for others, depending on how they were written.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.compat.h5py import decode
    >>> decode(b"ohm m"), decode(np.array(b"log10")), decode(3)
    ('ohm m', 'log10', 3)
    """
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if (
        isinstance(value, np.ndarray)
        and value.dtype.kind in "SO"
        and value.ndim == 0
    ):
        return decode(value[()])
    if isinstance(value, np.bytes_):
        return value.decode("utf-8")
    return value
