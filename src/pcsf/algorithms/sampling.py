"""Sampling of log-resistivity at arbitrary points.

This module implements the sampling operator
:math:`\\mathcal{S}_M(\\mathbf{p})` used to compare models of
different geometry. It needs NumPy only.

On rectilinear grids (``grid2d``, ``grid3d``) the operator is the
multilinear interpolation of :math:`m = \\log_{10}\\rho` between cell
centres; on triangular meshes it is point location, each point taking
the value of the triangle that contains it.

See Also
--------
pcsf.algorithms.locate : Point location used on meshes.
pcsf.algorithms.uncertainty : Propagation of uncertainty through the
    interpolation weights computed here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.schema import PCSFModel
from ..exceptions import GeometryError
from .locate import TriangleLocator

__all__ = [
    "InterpolationWeights",
    "interpolation_weights",
    "sample_log10",
]


def _axis_weights(
    q: np.ndarray,
    centres: np.ndarray,
    nodes: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bracketing cell, upper weight and outside mask on one axis.

    Parameters
    ----------
    q : ndarray of shape (n,)
        Query coordinates on this axis.
    centres : ndarray of shape (k,)
        Cell-centre coordinates, ascending or descending.
    nodes : ndarray of shape (k + 1,) or None
        Cell edges; when ``None`` the outer edges are placed half a
        cell beyond the outer centres.

    Returns
    -------
    i0 : ndarray of int
        Index of the lower bracketing cell, in the original order.
    t : ndarray of float
        Weight of cell ``i0 + 1``; cell ``i0`` has weight ``1 - t``.
    outside : ndarray of bool
        Queries beyond the outer cell edges.
    """
    c = np.asarray(centres, dtype=float)
    # Work on an ascending copy; map indices back at the end.
    flip = c.size > 1 and c[0] > c[-1]
    if flip:
        c = c[::-1]
    if nodes is not None:
        n = np.asarray(nodes, dtype=float)
        lo_edge, hi_edge = n.min(), n.max()
    elif c.size > 1:
        lo_edge = c[0] - (c[1] - c[0]) / 2
        hi_edge = c[-1] + (c[-1] - c[-2]) / 2
    else:
        lo_edge = hi_edge = c[0]
    outside = (q < lo_edge) | (q > hi_edge)
    if c.size == 1:
        i0 = np.zeros(q.shape, dtype=np.int64)
        t = np.zeros(q.shape)
    else:
        # Clipping to the outer centres gives the edge value between
        # the outer centre and the outer edge.
        qc = np.clip(q, c[0], c[-1])
        i0 = np.searchsorted(c, qc, side="right") - 1
        i0 = np.clip(i0, 0, c.size - 2)
        t = (qc - c[i0]) / (c[i0 + 1] - c[i0])
    if flip:
        i0, t = (c.size - 2) - i0, 1.0 - t
    return i0, t, outside


@dataclass
class InterpolationWeights:
    """Cells and weights of a multilinear interpolation.

    The interpolated value at point :math:`k` is
    :math:`\\sum_j w_{kj}\\, v_{c_{kj}}`, where :math:`c_{kj}` are the
    flat indices of the surrounding cells.

    Attributes
    ----------
    flat_index : ndarray of int, shape (n, K)
        Flat (C-order) indices of the ``K`` cells used for each of the
        ``n`` points; ``K = 4`` in 2D and ``K = 8`` in 3D.
    weights : ndarray of float, shape (n, K)
        Corresponding weights; each row sums to one.
    outside : ndarray of bool, shape (n,)
        Points outside the model; their results are NaN.

    See Also
    --------
    interpolation_weights : Build the weights for a grid model.
    pcsf.algorithms.interpolated_std : Standard deviation of
        interpolated values from these weights.

    Examples
    --------
    >>> import pcsf
    >>> from pcsf.algorithms import interpolation_weights
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0, 10.0], z=[5.0]),
    ...     resistivity=[[10.0, 1000.0]],
    ... )
    >>> w = interpolation_weights(model, [[2.5, 5.0]])
    >>> print(w.apply([[1.0, 3.0]]))
    [1.5]
    """

    flat_index: np.ndarray
    weights: np.ndarray
    outside: np.ndarray

    def apply(self, values: np.ndarray) -> np.ndarray:
        """Interpolate a cell field at the stored points.

        Parameters
        ----------
        values : array_like
            Field defined on the cells of the model, with the model's
            resistivity shape (it is flattened in C order).

        Returns
        -------
        ndarray of float, shape (n,)
            Interpolated values; NaN for points outside the model.
        """
        v = np.asarray(values, dtype=float).ravel()[self.flat_index]
        out = np.sum(v * self.weights, axis=1)
        out[self.outside] = np.nan
        return out


def interpolation_weights(
    model: PCSFModel, points: np.ndarray
) -> InterpolationWeights:
    """Multilinear interpolation weights for a grid model.

    Parameters
    ----------
    model : PCSFModel
        Model of kind ``grid2d`` or ``grid3d``.
    points : array_like
        Target points in the model frame, depth positive downward:
        shape ``(n, 2)`` as ``(x, z)`` for ``grid2d`` and ``(n, 3)``
        as ``(x, y, z)`` for ``grid3d``. Units are those of the model
        geometry (metres in practice).

    Returns
    -------
    InterpolationWeights
        Cell indices, weights and outside mask for each point.

    Raises
    ------
    GeometryError
        If the model is not a grid or the points have the wrong
        number of columns.

    See Also
    --------
    sample_log10 : Evaluate log10 resistivity with these weights.

    Notes
    -----
    On each axis a point :math:`q` lies between centres :math:`c_i`
    and :math:`c_{i+1}` with fraction
    :math:`t = (q - c_i)/(c_{i+1} - c_i)`; the weight of a corner cell
    is the product over axes of :math:`t` or :math:`1-t`. A point
    between the outermost centre and the outermost edge takes the
    edge-cell value (:math:`t` clipped); beyond the edge it is
    outside. The cost is :math:`O(n \\log k)` for :math:`k` cells per
    axis.

    Examples
    --------
    >>> import pcsf
    >>> from pcsf.algorithms import interpolation_weights
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0, 10.0], z=[5.0, 15.0]),
    ...     resistivity=[[1.0, 1.0], [1.0, 1.0]],
    ... )
    >>> w = interpolation_weights(model, [[5.0, 10.0]])
    >>> print(w.weights)
    [[0.25 0.25 0.25 0.25]]
    """
    pts = np.atleast_2d(np.asarray(points, dtype=float))
    geo = model.geometry
    if model.kind == "grid2d":
        if pts.shape[1] != 2:
            raise GeometryError(
                "grid2d points must have shape (n, 2) as (x, z)"
            )
        axes = [
            (geo.z, geo.z_nodes, pts[:, 1]),
            (geo.x, geo.x_nodes, pts[:, 0]),
        ]
        shape = (geo.z.size, geo.x.size)
    elif model.kind == "grid3d":
        if pts.shape[1] != 3:
            raise GeometryError(
                "grid3d points must have shape (n, 3) as (x, y, z)"
            )
        axes = [
            (geo.z, geo.z_nodes, pts[:, 2]),
            (geo.y, geo.y_nodes, pts[:, 1]),
            (geo.x, geo.x_nodes, pts[:, 0]),
        ]
        shape = (geo.z.size, geo.y.size, geo.x.size)
    else:
        raise GeometryError(
            f"interpolation weights need a grid, got {model.kind!r}"
        )
    per_axis = [_axis_weights(q, c, nd) for c, nd, q in axes]
    outside = np.zeros(len(pts), dtype=bool)
    for _, _, out_axis in per_axis:
        outside |= out_axis
    ndim = len(per_axis)
    # All 2**ndim corners as rows of 0/1 offsets.
    grids = np.meshgrid(*[[0, 1]] * ndim, indexing="ij")
    corners = np.array(grids).reshape(ndim, -1).T
    n, k = len(pts), corners.shape[0]
    flat = np.zeros((n, k), dtype=np.int64)
    weights = np.ones((n, k))
    strides = np.cumprod((1, *shape[::-1]))[:-1][::-1]
    for axis, (i0, t, _) in enumerate(per_axis):
        size = shape[axis]
        for j, bit in enumerate(corners[:, axis]):
            idx = np.clip(i0 + bit, 0, size - 1)
            flat[:, j] += idx * strides[axis]
            weights[:, j] *= t if bit else (1.0 - t)
    return InterpolationWeights(flat, weights, outside)


def sample_log10(model: PCSFModel, points: np.ndarray) -> np.ndarray:
    """Evaluate log10 resistivity of a model at arbitrary points.

    Parameters
    ----------
    model : PCSFModel
        Model of kind ``grid2d``, ``grid3d`` or ``mesh_unstructured``
        with canonical per-cell resistivity in ohm m.
    points : array_like
        Target points in the model frame, depth positive downward:
        ``(n, 2)`` as ``(x, z)`` for ``grid2d`` and meshes (planes
        ``"xz"`` and ``"xy"``), ``(n, 3)`` as ``(x, y, z)`` for
        ``grid3d``.

    Returns
    -------
    ndarray of float, shape (n,)
        :math:`\\log_{10}\\rho` at each point (decades of ohm m); NaN
        outside the model and where resistivity is undefined.

    Raises
    ------
    GeometryError
        If the geometry kind is unsupported, the points have the wrong
        shape, or a mesh does not have per-triangle resistivity.

    See Also
    --------
    interpolation_weights : Weights used on grids.
    pcsf.algorithms.compare_log10 : Statistics of two sampled fields.

    Notes
    -----
    The operator is

    .. math::

        \\mathcal{S}_M(\\mathbf{p}) =
        \\begin{cases}
        \\sum_c w_c(\\mathbf{p})\\, m_c & \\text{grids},\\\\
        m_{t(\\mathbf{p})} & \\text{triangular meshes},
        \\end{cases}

    with :math:`m_c = \\log_{10}\\rho_c` at cell centres,
    :math:`w_c` the multilinear weights, and :math:`t(\\mathbf{p})`
    the triangle containing :math:`\\mathbf{p}`. Interpolating
    :math:`m`, not :math:`\\rho`, weights relative changes equally in
    resistive and conductive parts of a model; on meshes the
    piecewise-constant rule keeps contrasts across region
    boundaries. The method is second order on smooth grid fields and
    first order on meshes.

    Examples
    --------
    >>> import pcsf
    >>> from pcsf.algorithms import sample_log10
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0, 10.0], z=[5.0]),
    ...     resistivity=[[10.0, 1000.0]],
    ... )
    >>> print(sample_log10(model, [[5.0, 5.0], [50.0, 5.0]]))
    [ 2. nan]
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        log_rho = np.log10(np.asarray(model.resistivity, dtype=float))
    if model.kind in ("grid2d", "grid3d"):
        return interpolation_weights(model, points).apply(log_rho)
    if model.kind != "mesh_unstructured":
        raise GeometryError(
            "sample_log10 does not support geometry kind "
            f"{model.kind!r}"
        )
    pts = np.atleast_2d(np.asarray(points, dtype=float))
    if pts.shape[1] != 2:
        raise GeometryError(
            "mesh points must have shape (n, 2) as (x, z)"
        )
    geo = model.geometry
    if geo.plane not in ("xz", "xy"):
        raise GeometryError(
            f"mesh plane {geo.plane!r} is not supported"
        )
    conn = np.asarray(geo.connectivity, dtype=np.int64)
    if log_rho.shape != (conn.shape[0],):
        raise GeometryError(
            "mesh sampling needs per-triangle resistivity of shape "
            f"({conn.shape[0]},), got {log_rho.shape}"
        )
    idx = TriangleLocator(geo.nodes, conn)(pts)
    out = np.full(len(pts), np.nan)
    inside = idx >= 0
    out[inside] = log_rho[idx[inside]]
    return out
