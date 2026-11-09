"""Exception hierarchy of pcsf.

Every error raised on purpose by pcsf derives from :class:`PCSFError`, so
that a caller can catch all of them with one clause::

    try:
        model = pcsf.read("model.pcsf")
    except pcsf.PCSFError as exc:
        ...

Each class also derives from the built-in exception that best describes
it (``ValueError``, ``KeyError``, ``ImportError``...), so that code written
against those built-ins keeps working.

Hierarchy::

    PCSFError
    ├── FormatError            malformed file or unreadable content
    │   └── PCSMSyntaxError    text (PCSM) that does not follow the grammar
    ├── VersionError           unsupported specification version
    ├── ConformanceError       a model that breaks a conformance rule
    ├── EncodingError          unknown or invalid resistivity encoding
    ├── GeometryError          inconsistent geometry or array shape
    ├── RegistryError          duplicate or missing registry entry
    ├── AdapterError           failure converting native solver output
    └── MissingDependencyError optional dependency not installed
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
    """

    def __init__(self, message: str, *, line: int | None = None) -> None:
        self.line = line
        super().__init__(f"line {line}: {message}" if line is not None else message)


class VersionError(PCSFError, ValueError):
    """A file declares a specification version this reader cannot read."""


class ConformanceError(PCSFError, ValueError):
    """A model breaks a conformance rule of the specification.

    Parameters
    ----------
    message : str
        Description of the problem.
    rule : str, optional
        Identifier of the rule that failed (e.g. ``"R1.positive"``).
    """

    def __init__(self, message: str, *, rule: str | None = None) -> None:
        self.rule = rule
        super().__init__(f"[{rule}] {message}" if rule else message)


class EncodingError(PCSFError, ValueError):
    """An unknown or invalid resistivity encoding."""


class GeometryError(PCSFError, ValueError):
    """A geometry or array shape is inconsistent."""


class RegistryError(PCSFError, KeyError):
    """A registry entry is duplicated or missing."""

    def __str__(self) -> str:  # KeyError quotes its message; keep it readable
        return str(self.args[0]) if self.args else ""


class AdapterError(PCSFError, RuntimeError):
    """Native solver output could not be converted."""


class MissingDependencyError(PCSFError, ImportError):
    """An optional dependency is needed but not installed.

    Parameters
    ----------
    package : str
        Name of the missing import.
    extra : str, optional
        The pcsf extra that installs it (``pip install pcsf[extra]``).
    feature : str, optional
        What needed it, for the error message.
    """

    def __init__(self, package: str, *, extra: str | None = None,
                 feature: str | None = None) -> None:
        self.package = package
        self.extra = extra
        what = f" for {feature}" if feature else ""
        hint = f' Install it with: pip install "pcsf[{extra}]"' if extra else \
            f" Install it with: pip install {package}"
        super().__init__(f"{package!r} is required{what}.{hint}", name=package)
