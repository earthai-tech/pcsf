"""Lazy imports of optional dependencies.

The core of pcsf needs only NumPy and h5py. Other packages are imported
when a feature needs them, through :func:`import_optional`, which raises a
:class:`~pcsf.exceptions.MissingDependencyError` that names the pcsf extra
to install.
"""

from __future__ import annotations

import importlib
import importlib.util
from types import ModuleType

from ..exceptions import MissingDependencyError

__all__ = ["OPTIONAL_DEPENDENCIES", "import_optional", "is_available"]

#: import name -> pcsf extra that installs it
OPTIONAL_DEPENDENCIES: dict[str, str] = {
    "scipy": "algorithms",
    "matplotlib": "algorithms",
    "netCDF4": "emc",
    "triangle": "mare2dem",
    "pyproj": "geo",
    "PySide6": "studio",
}


def is_available(name: str) -> bool:
    """Return whether module *name* can be imported, without importing it."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def import_optional(name: str, *, feature: str | None = None) -> ModuleType:
    """Import an optional dependency or raise a helpful error.

    Parameters
    ----------
    name : str
        Module to import, e.g. ``"scipy.interpolate"``.
    feature : str, optional
        What needs it, used in the error message.
    """
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        top = name.split(".")[0]
        raise MissingDependencyError(
            top, extra=OPTIONAL_DEPENDENCIES.get(top), feature=feature
        ) from exc
