"""Sampling of log-resistivity at arbitrary points (NumPy only).

The sampling operator :math:`\\mathcal{S}_M(\\mathbf{p})` of the paper:

* rectilinear grids (``grid2d``, ``grid3d``): multilinear interpolation of
  :math:`m = \\log_{10}\\rho` between cell centres,
  :math:`\\mathcal{S}_M(\\mathbf{p}) = \\sum_c w_c(\\mathbf{p})\\,m_c`;
  between the outermost cell centre and the outermost cell edge the edge
  value is used; outside the model the result is undefined (NaN);
* triangular meshes: point location, :math:`m_{t(\\mathbf{p})}` for the
  triangle :math:`t(\\mathbf{p})` that contains the point.

:func:`interpolation_weights` exposes the weights :math:`w_c` and cell
indices, so that uncertainties can be propagated exactly
(:mod:`pcsf.algorithms.uncertainty`).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.schema import PCSFModel
from ..exceptions import GeometryError
from .locate import TriangleLocator

__all__ = ["InterpolationWeights", "interpolation_weights", "sample_log10"]


def _axis_weights(q: np.ndarray, centres: np.ndarray, nodes: np.ndarray | None):
    """Lower index, weight of the upper neighbour, and outside mask, on one axis."""
    c = np.asarray(centres, dtype=float)
    flip = c.size > 1 and c[0] > c[-1]
    if flip:
        c = c[::-1]
    if nodes is not None:
        n = np.asarray(nodes, dtype=float)
        lo_n, hi_n = n.min(), n.max()
    elif c.size > 1:
        lo_n, hi_n = c[0] - (c[1] - c[0]) / 2, c[-1] + (c[-1] - c[-2]) / 2
    else:
        lo_n = hi_n = c[0]
    outside = (q < lo_n) | (q > hi_n)
    if c.size == 1:
        i0 = np.zeros(q.shape, dtype=np.int64)
        t = np.zeros(q.shape)
    else:
        qc = np.clip(q, c[0], c[-1])
        i0 = np.clip(np.searchsorted(c, qc, side="right") - 1, 0, c.size - 2)
        t = (qc - c[i0]) / (c[i0 + 1] - c[i0])
    if flip:
        n_ = c.size
        if n_ > 1:
            i0, t = (n_ - 2) - i0, 1.0 - t
    return i0, t, outside


@dataclass
class InterpolationWeights:
    """Cells and weights of multilinear interpolation.

    Attributes
    ----------
    flat_index : ndarray (n, k)
        Flat (C-order) indices into the resistivity array of the ``k``
        cells used for each of the ``n`` points (k = 4 in 2D, 8 in 3D).
    weights : ndarray (n, k)
        Corresponding weights; each row sums to 1.
    outside : ndarray (n,)
        Points outside the model (their result is NaN).
    """

    flat_index: np.ndarray
    weights: np.ndarray
    outside: np.ndarray

    def apply(self, values: np.ndarray) -> np.ndarray:
        """Interpolate a cell field (any array of the model's shape)."""
        v = np.asarray(values, dtype=float).ravel()[self.flat_index]
        out = np.sum(v * self.weights, axis=1)
        out[self.outside] = np.nan
        return out


def interpolation_weights(model: PCSFModel, points) -> InterpolationWeights:
    """Multilinear weights for a ``grid2d`` or ``grid3d`` model.

    Parameters
    ----------
    model : PCSFModel
    points : array-like
        ``(n, 2)`` as ``(x, z)`` for ``grid2d``; ``(n, 3)`` as ``(x, y, z)``
        for ``grid3d``; in the model frame, depth positive downward.
    """
    pts = np.atleast_2d(np.asarray(points, dtype=float))
    geo = model.geometry
    if model.kind == "grid2d":
        if pts.shape[1] != 2:
            raise GeometryError("grid2d points must have shape (n, 2) as (x, z)")
        axes = [(geo.z, geo.z_nodes, pts[:, 1]), (geo.x, geo.x_nodes, pts[:, 0])]
        shape = (geo.z.size, geo.x.size)
    elif model.kind == "grid3d":
        if pts.shape[1] != 3:
            raise GeometryError("grid3d points must have shape (n, 3) as (x, y, z)")
        axes = [(geo.z, geo.z_nodes, pts[:, 2]), (geo.y, geo.y_nodes, pts[:, 1]),
                (geo.x, geo.x_nodes, pts[:, 0])]
        shape = (geo.z.size, geo.y.size, geo.x.size)
    else:
        raise GeometryError(f"interpolation weights need a grid, got {model.kind!r}")
    per_axis = [_axis_weights(q, c, nd) for c, nd, q in axes]
    outside = np.zeros(len(pts), dtype=bool)
    for _, _, o in per_axis:
        outside |= o
    corners = np.array(np.meshgrid(*[[0, 1]] * len(per_axis), indexing="ij")).reshape(
        len(per_axis), -1).T                                    # (k, ndim)
    n, k = len(pts), corners.shape[0]
    flat = np.zeros((n, k), dtype=np.int64)
    w = np.ones((n, k))
    strides = np.cumprod((1,) + shape[::-1])[:-1][::-1]
    for a, (i0, t, _) in enumerate(per_axis):
        size = shape[a]
        for j, bit in enumerate(corners[:, a]):
            idx = np.clip(i0 + bit, 0, size - 1)
            flat[:, j] += idx * strides[a]
            w[:, j] *= t if bit else (1.0 - t)
    return InterpolationWeights(flat, w, outside)


def sample_log10(model: PCSFModel, points) -> np.ndarray:
    """Evaluate :math:`\\log_{10}\\rho` of *model* at *points*.

    Parameters
    ----------
    model : PCSFModel
        ``grid2d``, ``grid3d`` or ``mesh_unstructured`` model with
        canonical per-cell resistivity.
    points : array-like
        ``(n, 2)`` as ``(x, z)`` for ``grid2d`` and meshes (plane ``"xz"``);
        ``(n, 3)`` as ``(x, y, z)`` for ``grid3d``.

    Returns
    -------
    ndarray (n,)
        :math:`\\log_{10}\\rho`, NaN outside the model.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        log_rho = np.log10(np.asarray(model.resistivity, dtype=float))
    if model.kind in ("grid2d", "grid3d"):
        return interpolation_weights(model, points).apply(log_rho)
    if model.kind == "mesh_unstructured":
        pts = np.atleast_2d(np.asarray(points, dtype=float))
        if pts.shape[1] != 2:
            raise GeometryError("mesh points must have shape (n, 2) as (x, z)")
        geo = model.geometry
        if geo.plane not in ("xz", "xy"):
            raise GeometryError(f"mesh plane {geo.plane!r} is not supported")
        conn = np.asarray(geo.connectivity, dtype=np.int64)
        if log_rho.shape != (conn.shape[0],):
            raise GeometryError(
                f"mesh sampling needs per-triangle resistivity of shape ({conn.shape[0]},), "
                f"got {log_rho.shape}")
        idx = TriangleLocator(geo.nodes, conn)(pts)
        out = np.full(len(pts), np.nan)
        inside = idx >= 0
        out[inside] = log_rho[idx[inside]]
        return out
    raise GeometryError(f"sample_log10 does not support geometry kind {model.kind!r}")
