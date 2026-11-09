"""Exception hierarchy of pcsf.

Every error raised on purpose by pcsf derives from :class:`PCSFError`,
so that a caller can catch all of them with one clause. Each class
also derives from the built-in exception that best describes it
(``ValueError``, ``KeyError``, ``ImportError``, ``RuntimeError``), so
that code written against those built-ins keeps working.

Hierarchy::

    PCSFError
    |-- FormatError             malformed or unreadable file
    |   `-- PCSMSyntaxError     PCSM text breaking the grammar
    |-- VersionError            unsupported format version
    |-- ConformanceError        model breaking a rule
    |-- EncodingError           unknown or invalid encoding
    |-- GeometryError           inconsistent geometry or shape
    |-- RegistryError           duplicate or missing entry
    |-- AdapterError            native output not converted
    `-- MissingDependencyError  optional dependency missing

Examples
--------
>>> import pcsf
>>> try:
...     pcsf.read(__file__)
... except pcsf.PCSFError as exc:
...     type(exc).__name__
'FormatError'
"""

from __future__ import annotations

__all__ = [
    "AdapterError",
    "ConformanceError",
    "EncodingError",
    "FormatError",
    "GeometryError",
    "MissingDependencyError",
    "PCSFError",
    "PCSMSyntaxError",
    "RegistryError",
    "VersionError",
]


class PCSFError(Exception):
    """Base class of every error raised on purpose by pcsf."""


class FormatError(PCSFError, ValueError):
    """A file is malformed or its content cannot be interpreted."""


class PCSMSyntaxError(FormatError):
    """A PCSM text file does not follow the grammar.

    Parameters
    ----------
    message : str
        Description of the problem.
    line : int, optional
        1-based line number where the problem was detected.

    Attributes
    ----------
    line : int or None
        As given.

    Examples
    --------
    >>> from pcsf.exceptions import PCSMSyntaxError
    >>> str(PCSMSyntaxError("missing END", line=12))
    'line 12: missing END'
    """

    def __init__(
        self, message: str, *, line: int | None = None
    ) -> None:
        self.line = line
        if line is not None:
            message = f"line {line}: {message}"
        super().__init__(message)


class VersionError(PCSFError, ValueError):
    """A file declares a format version this reader cannot read."""


class ConformanceError(PCSFError, ValueError):
    """A model breaks a conformance rule of the specification.

    Parameters
    ----------
    message : str
        Description of the problem.
    rule : str, optional
        Identifier of the failed rule, such as ``"C1"``.

    Attributes
    ----------
    rule : str or None
        As given.

    Examples
    --------
    >>> from pcsf.exceptions import ConformanceError
    >>> str(ConformanceError("negative resistivity", rule="C2"))
    '[C2] negative resistivity'
    """

    def __init__(
        self, message: str, *, rule: str | None = None
    ) -> None:
        self.rule = rule
        super().__init__(f"[{rule}] {message}" if rule else message)


class EncodingError(PCSFError, ValueError):
    """An unknown or invalid resistivity encoding."""


class GeometryError(PCSFError, ValueError):
    """A geometry or array shape is inconsistent."""


class RegistryError(PCSFError, KeyError):
    """A registry entry is duplicated or missing."""

    def __str__(self) -> str:
        # KeyError quotes its message; keep it readable.
        return str(self.args[0]) if self.args else ""


class AdapterError(PCSFError, RuntimeError):
    """Native solver output could not be converted."""


class MissingDependencyError(PCSFError, ImportError):
    """An optional dependency is needed but not installed.

    Parameters
    ----------
    package : str
        Import name of the missing package.
    extra : str, optional
        The pcsf extra that installs it
        (``pip install "pcsf[extra]"``).
    feature : str, optional
        What needed it, for the error message.

    Attributes
    ----------
    package, extra : str or None
        As given.

    Examples
    --------
    >>> from pcsf.exceptions import MissingDependencyError
    >>> print(MissingDependencyError("pyproj", extra="geo"))
    'pyproj' is required. Install it with: pip install "pcsf[geo]"
    """

    def __init__(
        self,
        package: str,
        *,
        extra: str | None = None,
        feature: str | None = None,
    ) -> None:
        self.package = package
        self.extra = extra
        what = f" for {feature}" if feature else ""
        if extra:
            hint = f' Install it with: pip install "pcsf[{extra}]"'
        else:
            hint = f" Install it with: pip install {package}"
        super().__init__(
            f"{package!r} is required{what}.{hint}", name=package
        )
