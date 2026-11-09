"""File and path helpers."""

from __future__ import annotations

import gzip
import os
import tempfile
from pathlib import Path
from typing import IO

__all__ = ["atomic_write_bytes", "is_gzip", "open_text", "suffixes"]

_GZIP_MAGIC = b"\x1f\x8b"


def suffixes(path: str | os.PathLike[str]) -> str:
    """Lower-case compound suffix of a path.

    Parameters
    ----------
    path : str or os.PathLike
        File path; the file need not exist.

    Returns
    -------
    str
        Every suffix of the file name joined, such as
        ``".pcsm.gz"``; empty when there is none.

    Examples
    --------
    >>> from pcsf.utils.io import suffixes
    >>> suffixes("runs/Model.PCSM.gz")
    '.pcsm.gz'
    """
    return "".join(Path(path).suffixes).lower()


def is_gzip(path: str | os.PathLike[str]) -> bool:
    """Whether a file starts with the gzip magic number.

    Parameters
    ----------
    path : str or os.PathLike
        Existing file.

    Returns
    -------
    bool

    Raises
    ------
    OSError
        If the file cannot be opened.

    Examples
    --------
    >>> import gzip, os, tempfile
    >>> from pcsf.utils.io import is_gzip
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     path = os.path.join(tmp, "a.gz")
    ...     with gzip.open(path, "wb") as fh:
    ...         _ = fh.write(b"x")
    ...     is_gzip(path)
    True
    """
    with open(path, "rb") as fh:
        return fh.read(2) == _GZIP_MAGIC


def open_text(
    path: str | os.PathLike[str], mode: str = "rt"
) -> IO[str]:
    """Open a UTF-8 text file, gzip-compressed if it ends in ``.gz``.

    Parameters
    ----------
    path : str or os.PathLike
        File path; the ``.gz`` test is case-insensitive.
    mode : str, default "rt"
        Text mode, such as ``"rt"`` or ``"wt"``.

    Returns
    -------
    file object
        Text stream, to be used as a context manager.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.utils.io import open_text
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     path = os.path.join(tmp, "a.txt.gz")
    ...     with open_text(path, "wt") as fh:
    ...         _ = fh.write("ohm m")
    ...     with open_text(path) as fh:
    ...         fh.read()
    'ohm m'
    """
    if str(path).lower().endswith(".gz"):
        return gzip.open(path, mode, encoding="utf-8")
    return open(path, mode, encoding="utf-8")


def atomic_write_bytes(
    path: str | os.PathLike[str], data: bytes
) -> Path:
    """Write bytes so that readers never see a partial file.

    Parameters
    ----------
    path : str or os.PathLike
        Destination; its directory must exist.
    data : bytes
        Content.

    Returns
    -------
    pathlib.Path
        *path*.

    Raises
    ------
    OSError
        If the temporary file cannot be written or renamed; the
        temporary file is removed and *path* is left unchanged.

    Notes
    -----
    The data go to a temporary file in the same directory, which is
    then renamed over *path* with :func:`os.replace`, atomic on POSIX
    and Windows file systems.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.utils.io import atomic_write_bytes
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = atomic_write_bytes(os.path.join(tmp, "a.bin"), b"ab")
    ...     p.read_bytes()
    b'ab'
    """
    path = Path(path)
    fd, tmp = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path
