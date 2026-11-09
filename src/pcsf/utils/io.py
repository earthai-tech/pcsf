"""File and path helpers."""

from __future__ import annotations

import gzip
import os
import tempfile
from pathlib import Path

__all__ = ["atomic_write_bytes", "is_gzip", "open_text", "suffixes"]

_GZIP_MAGIC = b"\x1f\x8b"


def suffixes(path: str | os.PathLike[str]) -> str:
    """Lower-case compound suffix, e.g. ``".pcsm.gz"``."""
    return "".join(Path(path).suffixes).lower()


def is_gzip(path: str | os.PathLike[str]) -> bool:
    """Whether the file starts with the gzip magic number."""
    with open(path, "rb") as fh:
        return fh.read(2) == _GZIP_MAGIC


def open_text(path: str | os.PathLike[str], mode: str = "rt"):
    """Open a text file, transparently gzip-compressed if it ends in ``.gz``."""
    if str(path).lower().endswith(".gz"):
        return gzip.open(path, mode, encoding="utf-8")
    return open(path, mode, encoding="utf-8")


def atomic_write_bytes(path: str | os.PathLike[str], data: bytes) -> Path:
    """Write *data* to a temporary file, then rename it over *path*."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path
