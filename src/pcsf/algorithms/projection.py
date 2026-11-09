"""Node-to-cell projection of per-node resistivity.

Some predictors (graph networks, nodal finite elements) give
resistivity on mesh nodes, whereas PCSF stores it per cell. This
module averages the node values of each triangle.

See Also
--------
pcsf.algorithms.sample_log10 : Sampling of the projected model.
"""

from __future__ import annotations

import numpy as np

from ..exceptions import GeometryError

__all__ = ["NODE_AVERAGES", "node_to_cell"]

#: Averages accepted by :func:`node_to_cell`.
NODE_AVERAGES = ("arithmetic", "geometric")


def node_to_cell(
    connectivity: np.ndarray,
    node_rho: np.ndarray,
    average: str = "geometric",
) -> np.ndarray:
    """Per-cell resistivity from per-node resistivity.

    Parameters
    ----------
    connectivity : array_like of int, shape (n_cells, k)
        Node indices of each cell (``k = 3`` for triangles).
    node_rho : array_like of float, shape (n_nodes,)
        Resistivity at the nodes, in ohm m; must be positive for the
        geometric average.
    average : {"geometric", "arithmetic"}, default "geometric"
        Averaging rule, :math:`\\Pi_g` or :math:`\\Pi_a` below.

    Returns
    -------
    ndarray of float, shape (n_cells,)
        Resistivity of each cell in ohm m.

    Raises
    ------
    GeometryError
        If the connectivity references a node outside *node_rho*, or
        *average* is unknown.

    Notes
    -----
    For a cell :math:`t` with vertex set :math:`V(t)`,

    .. math::

        \\Pi_a:\\ \\rho(t) = \\frac{1}{|V(t)|}
        \\sum_{v\\in V(t)} \\rho(v),\\qquad
        \\Pi_g:\\ \\log_{10}\\rho(t) = \\frac{1}{|V(t)|}
        \\sum_{v\\in V(t)} \\log_{10}\\rho(v).

    :math:`\\Pi_g` is the geometric mean; it treats a contrast the
    same way in resistive and conductive ground, and is the default.
    :math:`\\Pi_a` is biased toward the most resistive node and is
    kept for compatibility with tools that use it.

    Examples
    --------
    >>> from pcsf.algorithms import node_to_cell
    >>> rho = [10.0, 100.0, 1000.0]
    >>> print(node_to_cell([[0, 1, 2]], rho))
    [100.]
    >>> print(node_to_cell([[0, 1, 2]], rho, average="arithmetic"))
    [370.]
    """
    conn = np.asarray(connectivity, dtype=np.int64)
    vals = np.asarray(node_rho, dtype=float)
    if conn.size and (conn.min() < 0 or conn.max() >= vals.size):
        raise GeometryError(
            "connectivity references an out-of-range node"
        )
    v = vals[conn]
    if average == "arithmetic":
        return v.mean(axis=1)
    if average == "geometric":
        return 10.0 ** np.log10(v).mean(axis=1)
    raise GeometryError(
        f"average must be one of {NODE_AVERAGES}, got {average!r}"
    )
