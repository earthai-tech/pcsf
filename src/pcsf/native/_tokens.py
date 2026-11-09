"""Line and token helpers shared by the native parsers."""

from __future__ import annotations

import os
import re
from pathlib import Path

from ..exceptions import FormatError

__all__ = ["file_number", "header_value", "read_lines"]

_NUMBER = re.compile(r"\d+")


def read_lines(path: str | os.PathLike[str]) -> list[str]:
    """Lines of a text file, without line endings.

    Parameters
    ----------
    path : str or os.PathLike
        File to read; undecodable bytes are replaced.

    Returns
    -------
    list of str

    Raises
    ------
    FormatError
        If the file does not exist.
    """
    p = Path(path)
    if not p.is_file():
        raise FormatError(f"file not found: {p}")
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        return [line.rstrip("\r\n") for line in fh]


def header_value(line: str) -> tuple[str, str] | None:
    """Split a ``Key: value`` header line.

    Parameters
    ----------
    line : str
        One line of a file.

    Returns
    -------
    tuple of str or None
        Upper-case key and stripped value, or ``None`` when the line
        has no colon.

    Examples
    --------
    >>> from pcsf.native._tokens import header_value
    >>> header_value("Misfit Value:   7.80")
    ('MISFIT VALUE', '7.80')
    """
    if ":" not in line:
        return None
    key, _, value = line.partition(":")
    return key.strip().upper(), value.strip()


def file_number(path: str | os.PathLike[str]) -> int:
    """First integer in a file stem, ``-1`` when there is none.

    Parameters
    ----------
    path : str or os.PathLike
        File path.

    Returns
    -------
    int

    Examples
    --------
    >>> from pcsf.native._tokens import file_number
    >>> file_number("ITER054.iter"), file_number("model.rho")
    (54, -1)
    """
    match = _NUMBER.search(Path(path).stem)
    return int(match.group()) if match else -1
