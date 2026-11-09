"""SHA-256 digests of files and arrays."""

from __future__ import annotations

import hashlib
import os

import numpy as np

__all__ = ["sha256_array", "sha256_file"]


def sha256_file(
    path: str | os.PathLike[str], *, chunk_size: int = 1 << 20
) -> str:
    """SHA-256 of a file, read in chunks.

    Parameters
    ----------
    path : str or os.PathLike
        File to hash.
    chunk_size : int, default 1 MiB
        Bytes read at a time; bounds memory use.

    Returns
    -------
    str
        Lower-case hexadecimal digest (64 characters).

    Raises
    ------
    OSError
        If the file cannot be read.

    See Also
    --------
    sha256_array : Digest of an in-memory array.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.utils.hashing import sha256_file
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     path = os.path.join(tmp, "empty")
    ...     open(path, "wb").close()
    ...     sha256_file(path)[:16]
    'e3b0c44298fc1c14'
    """
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    """SHA-256 of an array's dtype, shape and C-ordered bytes.

    Parameters
    ----------
    arr : array_like
        Array to hash.

    Returns
    -------
    str
        Lower-case hexadecimal digest.

    Notes
    -----
    The dtype string (with byte order) and the shape enter the digest,
    so arrays with the same bytes but a different dtype or shape have
    different digests. Memory layout does not: a Fortran-ordered array
    hashes like its C-ordered copy.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.utils.hashing import sha256_array
    >>> a = np.arange(6.0).reshape(2, 3)
    >>> sha256_array(a) == sha256_array(np.asfortranarray(a))
    True
    >>> sha256_array(a) == sha256_array(a.reshape(3, 2))
    False
    """
    a = np.ascontiguousarray(arr)
    digest = hashlib.sha256()
    digest.update(str(a.dtype.str).encode())
    digest.update(str(a.shape).encode())
    digest.update(a.tobytes())
    return digest.hexdigest()
