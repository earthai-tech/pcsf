"""Encodings of source (native) values and their conversion to resistivity.

Every PCSF file stores the canonical field as linear resistivity in ohm m.
When a source stores another quantity or scale, the source values are kept
next to it together with the name of their encoding, and the canonical
values follow from

.. math::

    \\rho = C_e(r) =
    \\begin{cases}
    10^{r} & e = \\texttt{log10}\\\\
    \\exp(r) & e = \\texttt{ln}\\\\
    r & e = \\texttt{linear}\\\\
    10^{-r} & e = \\texttt{log10\\_conductivity}\\\\
    1/r & e = \\texttt{conductivity}
    \\end{cases}

New encodings are added with :func:`pcsf.api.registry.register_encoding`,
without changing this module.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..api.registry import ENCODINGS, EncodingSpec, get_encoding

__all__ = [
    "BUILTIN_ENCODINGS",
    "from_resistivity",
    "is_known_encoding",
    "known_encodings",
    "to_resistivity",
]


def _inv(values: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore"):
        return 1.0 / values


def _register_builtins() -> None:
    builtins = [
        EncodingSpec("log10", lambda r: 10.0 ** r, np.log10, "resistivity",
                     "log10 of resistivity in ohm m (Occam2D)"),
        EncodingSpec("ln", np.exp, np.log, "resistivity",
                     "natural log of resistivity in ohm m (ModEM)"),
        EncodingSpec("linear", lambda r: r, lambda rho: rho, "resistivity",
                     "resistivity in ohm m (MARE2DEM)"),
        EncodingSpec("log10_conductivity", lambda r: 10.0 ** (-r), lambda rho: -np.log10(rho),
                     "conductivity", "log10 of conductivity in S/m (EMC archive)"),
        EncodingSpec("conductivity", _inv, _inv, "conductivity", "conductivity in S/m"),
    ]
    for spec in builtins:
        if spec.name not in ENCODINGS:
            ENCODINGS.register(spec.name, spec)


_register_builtins()

#: The encodings defined by the specification itself.
BUILTIN_ENCODINGS = ("log10", "ln", "linear", "log10_conductivity", "conductivity")


def known_encodings() -> tuple[str, ...]:
    """Every registered encoding (built-in and plugin)."""
    return ENCODINGS.names()


def is_known_encoding(name: Any) -> bool:
    """Whether *name* is a registered encoding."""
    return isinstance(name, str) and name in ENCODINGS


def to_resistivity(values: Any, encoding: str) -> np.ndarray:
    """Convert source *values* in *encoding* to linear resistivity (ohm m)."""
    return get_encoding(encoding)(values)


def from_resistivity(rho: Any, encoding: str) -> np.ndarray:
    """Convert linear resistivity to source values in *encoding*."""
    spec = get_encoding(encoding)
    if spec.from_resistivity is None:
        raise NotImplementedError(f"encoding {encoding!r} has no inverse")
    return spec.from_resistivity(np.asarray(rho, dtype=float))
