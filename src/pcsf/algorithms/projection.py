"""Node-to-cell projection for per-node (graph) predictions.

For a triangle :math:`t` with vertex set :math:`V(t)`:

.. math::

    \\Pi_a:\\ \\rho(t) = \\frac{1}{|V(t)|}\\sum_{v\\in V(t)}\\rho(v),\\qquad
    \\Pi_g:\\ m(t) = \\frac{1}{|V(t)|}\\sum_{v\\in V(t)} m(v),\\quad m = \\log_{10}\\rho.

:math:`\\Pi_g` (geometric mean) was more accurate than :math:`\\Pi_a` at
every cell size in the accuracy test of the paper and is the
recommended choice; :math:`\\Pi_a` is kept for compatibility.
"""

from __future__ import annotations

import numpy as np

from ..exceptions import GeometryError

__all__ = ["NODE_AVERAGES", "node_to_cell"]

NODE_AVERAGES = ("arithmetic", "geometric")


def node_to_cell(connectivity, node_rho, average: str = "geometric") -> np.ndarray:
    """Per-triangle resistivity from per-node resistivity (ohm m)."""
    conn = np.asarray(connectivity, dtype=np.int64)
    vals = np.asarray(node_rho, dtype=float)
    if conn.size and (conn.min() < 0 or conn.max() >= vals.size):
        raise GeometryError("connectivity references an out-of-range node")
    v = vals[conn]
    if average == "arithmetic":
        return v.mean(axis=1)
    if average == "geometric":
        return 10.0 ** np.log10(v).mean(axis=1)
    raise GeometryError(f"average must be one of {NODE_AVERAGES}, got {average!r}")
