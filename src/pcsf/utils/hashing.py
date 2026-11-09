"""SHA-256 helpers."""

from __future__ import annotations

import hashlib
import os

import numpy as np

__all__ = ["sha256_array", "sha256_file"]


def sha256_file(path: str | os.PathLike[str], *, chunk_size: int = 1 << 20) -> str:
    """Lower-case hex SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    """SHA-256 of an array's dtype, shape and C-ordered bytes."""
    a = np.ascontiguousarray(arr)
    digest = hashlib.sha256()
    digest.update(str(a.dtype.str).encode())
    digest.update(str(a.shape).encode())
    digest.update(a.tobytes())
    return digest.hexdigest()
