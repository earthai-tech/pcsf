"""Discovery of third-party extensions through entry points.

A package extends pcsf by exposing a zero-argument function under one of
these entry-point groups in its ``pyproject.toml``::

    [project.entry-points."pcsf.encodings"]
    my_encodings = "my_package.pcsf_plugin:register_encodings"

    [project.entry-points."pcsf.adapters"]
    my_solver = "my_package.pcsf_plugin:register_adapters"

    [project.entry-points."pcsf.formats"]
    boreholes = "my_package.pcsf_plugin:register_formats"

The function calls the registration helpers of :mod:`pcsf.api.registry`.

Discovery never runs at import time: no third-party code executes just
because a package is installed. Call :func:`load_plugins` explicitly; the
``pcsf`` command-line tool calls it before every command.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

from ..compat.python import entry_points

__all__ = ["GROUPS", "PluginResult", "load_plugins"]

GROUPS = ("pcsf.encodings", "pcsf.adapters", "pcsf.formats")


@dataclass(frozen=True)
class PluginResult:
    """Outcome of loading one entry point."""

    group: str
    name: str
    ok: bool
    error: str | None = None


_loaded: set[tuple[str, str]] = set()


def load_plugins(groups=GROUPS, *, on_error: str = "warn") -> list[PluginResult]:
    """Load and run every registered entry point of *groups* once.

    Parameters
    ----------
    on_error : {"warn", "raise", "ignore"}
        What to do when a plugin fails to load.
    """
    results = []
    for group in groups:
        for ep in entry_points(group):
            key = (group, ep.name)
            if key in _loaded:
                continue
            try:
                ep.load()()
                _loaded.add(key)
                results.append(PluginResult(group, ep.name, True))
            except Exception as exc:  # report, never crash the host
                results.append(PluginResult(group, ep.name, False, str(exc)))
                if on_error == "raise":
                    raise
                if on_error == "warn":
                    warnings.warn(f"pcsf plugin {ep.name!r} ({group}) failed: {exc}",
                                  RuntimeWarning, stacklevel=2)
    return results
