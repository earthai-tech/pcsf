"""Lazy imports of optional dependencies.

The core of pcsf needs only NumPy and h5py. Other packages are
imported when a feature needs them, through :func:`import_optional`,
which raises a :class:`~pcsf.exceptions.MissingDependencyError` that
names the pcsf extra to install.
"""

from __future__ import annotations

import importlib
import importlib.util
from types import ModuleType

from ..exceptions import MissingDependencyError

__all__ = ["OPTIONAL_DEPENDENCIES", "import_optional", "is_available"]

#: Top-level import name to the pcsf extra that installs it.
OPTIONAL_DEPENDENCIES: dict[str, str] = {
    "scipy": "algorithms",
    "matplotlib": "algorithms",
    "netCDF4": "emc",
    "triangle": "mare2dem",
    "pyproj": "geo",
    "PySide6": "studio",
}


def is_available(name: str) -> bool:
    """Whether a module can be imported, without importing it.

    Parameters
    ----------
    name : str
        Module name, possibly dotted.

    Returns
    -------
    bool
        True when an import spec is found. For a dotted name the
        parent package is imported to search it.

    See Also
    --------
    import_optional : Import or raise a helpful error.

    Examples
    --------
    >>> from pcsf.compat import is_available
    >>> is_available("numpy"), is_available("not_a_real_module_xyz")
    (True, False)
    """
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def import_optional(
    name: str, *, feature: str | None = None
) -> ModuleType:
    """Import an optional dependency or raise a helpful error.

    Parameters
    ----------
    name : str
        Module to import, such as ``"scipy.interpolate"``.
    feature : str, optional
        What needs it, used in the error message.

    Returns
    -------
    module
        The imported module.

    Raises
    ------
    MissingDependencyError
        If the import fails; the message names the pcsf extra listed
        in :data:`OPTIONAL_DEPENDENCIES` for the top-level package.

    See Also
    --------
    pcsf.decorators.requires : Same check as a decorator.

    Examples
    --------
    >>> from pcsf.compat import import_optional
    >>> import_optional("json").__name__
    'json'
    """
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        top = name.split(".")[0]
        raise MissingDependencyError(
            top,
            extra=OPTIONAL_DEPENDENCIES.get(top),
            feature=feature,
        ) from exc
