"""Encodings of source values and their conversion to resistivity.

Every PCSF file stores the canonical field as linear resistivity in
ohm m. When a source stores another quantity or scale, its values are
kept next to the canonical field together with the name of their
encoding.

Notes
-----
With :math:`r` the source value and :math:`e` its encoding, the
canonical resistivity is

.. math::

    \\rho = C_e(r) =
    \\begin{cases}
    10^{r} & e = \\texttt{log10},\\\\
    \\exp(r) & e = \\texttt{ln},\\\\
    r & e = \\texttt{linear},\\\\
    10^{-r} & e = \\texttt{log10\\_conductivity},\\\\
    1/r & e = \\texttt{conductivity},
    \\end{cases}

with conductivity in S/m. New encodings are added with
:func:`pcsf.api.registry.register_encoding`, without changing this
module.
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
    """Reciprocal; zero conductivity maps to infinite resistivity."""
    with np.errstate(divide="ignore"):
        return 1.0 / values


def _register_builtins() -> None:
    """Register the encodings of the specification (idempotent)."""
    builtins = [
        EncodingSpec(
            "log10",
            lambda r: 10.0**r,
            np.log10,
            "resistivity",
            "log10 of resistivity in ohm m (Occam2D)",
        ),
        EncodingSpec(
            "ln",
            np.exp,
            np.log,
            "resistivity",
            "natural log of resistivity in ohm m (ModEM)",
        ),
        EncodingSpec(
            "linear",
            lambda r: r,
            lambda rho: rho,
            "resistivity",
            "resistivity in ohm m (MARE2DEM)",
        ),
        EncodingSpec(
            "log10_conductivity",
            lambda r: 10.0 ** (-r),
            lambda rho: -np.log10(rho),
            "conductivity",
            "log10 of conductivity in S/m (EMC archive)",
        ),
        EncodingSpec(
            "conductivity",
            _inv,
            _inv,
            "conductivity",
            "conductivity in S/m",
        ),
    ]
    for spec in builtins:
        if spec.name not in ENCODINGS:
            ENCODINGS.register(spec.name, spec)


_register_builtins()

#: The encodings defined by the specification itself.
BUILTIN_ENCODINGS = (
    "log10",
    "ln",
    "linear",
    "log10_conductivity",
    "conductivity",
)


def known_encodings() -> tuple[str, ...]:
    """Names of every registered encoding, built-in and plugin.

    Returns
    -------
    tuple of str
        Sorted names.

    Examples
    --------
    >>> from pcsf.core.encodings import known_encodings
    >>> "log10_conductivity" in known_encodings()
    True
    """
    return ENCODINGS.names()


def is_known_encoding(name: Any) -> bool:
    """Whether a value names a registered encoding.

    Parameters
    ----------
    name : object
        Candidate name; non-strings are never known.

    Returns
    -------
    bool

    Examples
    --------
    >>> from pcsf.core.encodings import is_known_encoding
    >>> is_known_encoding("ln"), is_known_encoding("log2")
    (True, False)
    """
    return isinstance(name, str) and name in ENCODINGS


def to_resistivity(values: Any, encoding: str) -> np.ndarray:
    """Convert source values to linear resistivity.

    Parameters
    ----------
    values : array_like
        Source values in *encoding*.
    encoding : str
        Registered encoding name.

    Returns
    -------
    ndarray of float
        :math:`\\rho = C_e(r)` in ohm m, same shape as *values*.

    Raises
    ------
    EncodingError
        If *encoding* is not registered.

    See Also
    --------
    from_resistivity : Inverse conversion.

    Examples
    --------
    >>> from pcsf.core.encodings import to_resistivity
    >>> print(to_resistivity([2.0, -1.0], "log10_conductivity"))
    [ 0.01 10.  ]
    """
    return get_encoding(encoding)(values)


def from_resistivity(rho: Any, encoding: str) -> np.ndarray:
    """Convert linear resistivity to source values.

    Parameters
    ----------
    rho : array_like
        Resistivity in ohm m.
    encoding : str
        Registered encoding name.

    Returns
    -------
    ndarray of float
        :math:`r = C_e^{-1}(\\rho)`, same shape as *rho*.

    Raises
    ------
    EncodingError
        If *encoding* is not registered.
    NotImplementedError
        If the encoding was registered without an inverse.

    See Also
    --------
    to_resistivity : Forward conversion.

    Examples
    --------
    >>> from pcsf.core.encodings import from_resistivity
    >>> print(from_resistivity([10.0, 1000.0], "log10"))
    [1. 3.]
    """
    spec = get_encoding(encoding)
    if spec.from_resistivity is None:
        raise NotImplementedError(
            f"encoding {encoding!r} has no inverse"
        )
    return spec.from_resistivity(np.asarray(rho, dtype=float))
