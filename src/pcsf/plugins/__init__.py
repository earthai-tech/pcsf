"""Discovery of third-party extensions through entry points.

A package extends pcsf by exposing a zero-argument function under one
of these entry-point groups in its ``pyproject.toml``::

    [project.entry-points."pcsf.encodings"]
    my_encodings = "my_package.pcsf_plugin:register_encodings"

    [project.entry-points."pcsf.adapters"]
    my_solver = "my_package.pcsf_plugin:register_adapters"

    [project.entry-points."pcsf.formats"]
    boreholes = "my_package.pcsf_plugin:register_formats"

The function calls the registration helpers of
:mod:`pcsf.api.registry`.

Discovery never runs at import time, so that no third-party code
executes just because a package is installed. Call
:func:`load_plugins` explicitly; the ``pcsf`` command-line tool calls
it before every command.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from dataclasses import dataclass

from ..compat.python import entry_points

__all__ = ["GROUPS", "PluginResult", "load_plugins"]

#: Entry-point groups searched by :func:`load_plugins`.
GROUPS = ("pcsf.encodings", "pcsf.adapters", "pcsf.formats")

_ON_ERROR = ("warn", "raise", "ignore")

# Entry points already run in this process, as (group, name).
_loaded: set[tuple[str, str]] = set()


@dataclass(frozen=True)
class PluginResult:
    """Outcome of loading one entry point.

    Attributes
    ----------
    group : str
        Entry-point group.
    name : str
        Entry-point name.
    ok : bool
        True when the registration function ran without error.
    error : str or None, default None
        Error message when ``ok`` is False.
    """

    group: str
    name: str
    ok: bool
    error: str | None = None


def load_plugins(
    groups: Iterable[str] = GROUPS, *, on_error: str = "warn"
) -> list[PluginResult]:
    """Load and run the registered entry points of some groups.

    Parameters
    ----------
    groups : iterable of str, default GROUPS
        Entry-point groups to search.
    on_error : {"warn", "raise", "ignore"}, default "warn"
        What to do when a plugin fails: warn and continue, re-raise
        its exception, or continue silently. Failures are reported in
        the result in every case except ``"raise"``.

    Returns
    -------
    list of PluginResult
        One entry per entry point attempted in this call. Entry
        points that succeeded in an earlier call are skipped.

    Raises
    ------
    ValueError
        If *on_error* is not one of the accepted values.
    Exception
        The plugin's own exception when *on_error* is ``"raise"``.

    Warns
    -----
    RuntimeWarning
        For each failed plugin when *on_error* is ``"warn"``.

    Notes
    -----
    A failing plugin never stops the others from loading unless
    *on_error* is ``"raise"``; a broken extension must not break the
    host application.

    Examples
    --------
    >>> from pcsf.plugins import load_plugins
    >>> load_plugins(groups=("pcsf.no_such_group",))
    []
    """
    if on_error not in _ON_ERROR:
        raise ValueError(
            f"on_error must be one of {_ON_ERROR}, got {on_error!r}"
        )
    results = []
    for group in groups:
        for ep in entry_points(group):
            key = (group, ep.name)
            if key in _loaded:
                continue
            try:
                ep.load()()
            except Exception as exc:
                # A broken plugin must not break the host (Notes).
                results.append(
                    PluginResult(group, ep.name, False, str(exc))
                )
                if on_error == "raise":
                    raise
                if on_error == "warn":
                    warnings.warn(
                        f"pcsf plugin {ep.name!r} ({group}) "
                        f"failed: {exc}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
            else:
                _loaded.add(key)
                results.append(PluginResult(group, ep.name, True))
    return results
