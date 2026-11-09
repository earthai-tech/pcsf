"""Format-version parsing and checking shared by both encodings.

:mod:`pcsf.core.hdf5` (``.pcsf``) and :mod:`pcsf.core.text`
(``.pcsm``) serialise the same :class:`~pcsf.core.schema.PCSFModel`,
so they share one implementation of the versioning policy of the
specification (``spec/``, section 5) rather than two copies that
could drift apart.

Notes
-----
Format versions are ``MAJOR.MINOR.PATCH``. A reader rejects a file
of another major version, accepts an older or equal minor version,
and reads a newer minor version with a warning, ignoring the fields
it does not know. The format version is independent of the package
version.
"""

from __future__ import annotations

import warnings

from .._version import FORMAT_VERSION
from ..exceptions import VersionError

__all__ = ["check_pcsf_version", "parse_pcsf_version"]


def parse_pcsf_version(text: str) -> tuple[int, int, int]:
    """Parse a ``MAJOR.MINOR.PATCH`` format version.

    Parameters
    ----------
    text : str
        Version string, such as ``"0.1.0"``.

    Returns
    -------
    tuple of int
        ``(major, minor, patch)``.

    Raises
    ------
    VersionError
        If *text* does not have three integer parts.

    Examples
    --------
    >>> from pcsf.core.versioning import parse_pcsf_version
    >>> parse_pcsf_version("0.1.2")
    (0, 1, 2)
    """
    expected = (
        f"malformed pcsf_version {text!r}; expected MAJOR.MINOR.PATCH"
    )
    parts = text.split(".")
    if len(parts) != 3:
        raise VersionError(expected)
    try:
        major, minor, patch = (int(part) for part in parts)
    except ValueError as exc:
        raise VersionError(expected) from exc
    return major, minor, patch


def check_pcsf_version(
    file_version: str, reader_version: str = FORMAT_VERSION
) -> None:
    """Apply the versioning policy to the version of a file.

    Parameters
    ----------
    file_version : str
        Version declared by the file.
    reader_version : str, default FORMAT_VERSION
        Version implemented by this reader.

    Raises
    ------
    VersionError
        If either version is malformed or the major versions differ.

    Warns
    -----
    UserWarning
        If the file's minor version is newer than the reader's.

    Examples
    --------
    >>> from pcsf.core.versioning import check_pcsf_version
    >>> check_pcsf_version("0.1.0", reader_version="0.1.0")
    >>> check_pcsf_version("1.0.0", reader_version="0.1.0")
    Traceback (most recent call last):
    ...
    pcsf.exceptions.VersionError: unsupported pcsf_version '1.0.0'...
    """
    current_major, current_minor, _ = parse_pcsf_version(
        reader_version
    )
    file_major, file_minor, _ = parse_pcsf_version(file_version)
    if file_major != current_major:
        raise VersionError(
            f"unsupported pcsf_version {file_version!r}: this reader "
            f"only recognises major version {current_major} (reader "
            f"PCSF_VERSION={reader_version!r}); see the PCSF "
            "specification (spec/) section 5 for the versioning policy"
        )
    if file_minor > current_minor:
        warnings.warn(
            f"file was written with pcsf_version {file_version!r}, "
            f"newer than this reader's {reader_version!r}; fields "
            "added since then will be ignored",
            stacklevel=2,
        )
