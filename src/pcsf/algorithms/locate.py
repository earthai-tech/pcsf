"""Point location in a triangular mesh.

The locator answers, for each query point, which triangle contains
it. It needs NumPy only and serves both mesh sampling
(:func:`pcsf.algorithms.sample_log10`) and the mesh-to-grid export
(:func:`pcsf.algorithms.mesh_to_grid2d`).

Notes
-----
Triangles are binned on a regular grid of buckets covering the mesh
bounding box; a point is then tested only against the triangles of
its bucket, with barycentric coordinates. With about two triangles
per bucket, building costs :math:`O(m)` and locating :math:`n`
points :math:`O(n)` on typical meshes; large padding triangles are
entered in every bucket they cover.

A point on an edge or vertex shared by several triangles is assigned
to the one with the lowest index, so that results are deterministic.
"""

from __future__ import annotations

import numpy as np

__all__ = ["TriangleLocator", "locate_triangles"]

#: Absolute tolerance of the barycentric inside test.
_EPS = 1e-12


class TriangleLocator:
    """Reusable point locator for one triangular mesh.

    Parameters
    ----------
    nodes : array_like of shape (n_nodes, 2) or (n_nodes, 3)
        Node coordinates; only the first two columns are used.
    connectivity : array_like of int, shape (n_triangles, 3)
        Node indices of each triangle.
    bucket_size : float, default 2.0
        Target number of triangles per bucket. Smaller values use
        more memory and test fewer triangles per point.

    Attributes
    ----------
    nodes : ndarray of shape (n_nodes, 2)
        Node coordinates.
    tri : ndarray of int, shape (n_triangles, 3)
        Connectivity.
    bbox : tuple of ndarray
        Lower-left and upper-right corners of the mesh.

    See Also
    --------
    locate_triangles : One-shot convenience function.

    Notes
    -----
    A point :math:`\\mathbf{q}` lies in the triangle of
    vertices :math:`\\mathbf{a}, \\mathbf{b}, \\mathbf{c}` when
    its barycentric coordinates :math:`u, v`, defined by
    :math:`\\mathbf{q} - \\mathbf{a} = u(\\mathbf{b}-\\mathbf{a})
    + v(\\mathbf{c}-\\mathbf{a})`, satisfy :math:`u \\ge 0`,
    :math:`v \\ge 0` and :math:`u + v \\le 1`, within an absolute
    tolerance of :math:`10^{-12}`. Degenerate (zero-area) triangles
    never match.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.algorithms import TriangleLocator
    >>> nodes = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0],
    ...                   [1.0, 1.0]])
    >>> locate = TriangleLocator(nodes, [[0, 1, 2], [1, 3, 2]])
    >>> print(locate([[0.2, 0.2], [0.8, 0.8], [2.0, 2.0]]))
    [ 0  1 -1]
    """

    def __init__(
        self,
        nodes: np.ndarray,
        connectivity: np.ndarray,
        *,
        bucket_size: float = 2.0,
    ) -> None:
        self.nodes = np.asarray(nodes, dtype=float)[:, :2]
        self.tri = np.asarray(connectivity, dtype=np.int64)
        corners = self.nodes[self.tri]  # (m, 3, 2)
        self._a = corners[:, 0]
        self._v0 = corners[:, 1] - corners[:, 0]
        self._v1 = corners[:, 2] - corners[:, 0]
        self._det = (
            self._v0[:, 0] * self._v1[:, 1]
            - self._v0[:, 1] * self._v1[:, 0]
        )
        lo, hi = corners.min(axis=1), corners.max(axis=1)
        self.bbox = (lo.min(axis=0), hi.max(axis=0))
        m = len(self.tri)
        span = np.maximum(self.bbox[1] - self.bbox[0], _EPS)
        n_b = max(1, int(np.sqrt(m / max(bucket_size, 1e-9))))
        aspect = span[0] / span[1]
        nx = max(1, int(np.rint(n_b * np.sqrt(aspect))))
        ny = max(1, int(np.rint(n_b / np.sqrt(aspect))))
        self._shape = (nx, ny)
        self._cell = span / np.array([nx, ny])
        i0, j0 = self._bucket(lo)
        i1, j1 = self._bucket(hi)
        # Enter each triangle in every bucket its bounding box covers.
        counts = (i1 - i0 + 1) * (j1 - j0 + 1)
        tri_ids = np.repeat(np.arange(m), counts)
        offset = np.arange(counts.sum()) - np.repeat(
            np.cumsum(counts) - counts, counts
        )
        width = np.repeat(i1 - i0 + 1, counts)
        bi = np.repeat(i0, counts) + offset % width
        bj = np.repeat(j0, counts) + offset // width
        key = bi * ny + bj
        order = np.argsort(key, kind="stable")
        self._bucket_tris = tri_ids[order]
        self._bucket_start = np.searchsorted(
            key[order], np.arange(nx * ny + 1)
        )

    def _bucket(self, xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Bucket indices of points, clipped to the bucket grid."""
        scaled = (xy - self.bbox[0]) / self._cell
        ij = np.floor(scaled).astype(np.int64)
        return (
            np.clip(ij[..., 0], 0, self._shape[0] - 1),
            np.clip(ij[..., 1], 0, self._shape[1] - 1),
        )

    def __call__(self, points: np.ndarray) -> np.ndarray:
        """Locate points.

        Parameters
        ----------
        points : array_like of shape (n, 2)
            Query points; extra columns are ignored.

        Returns
        -------
        ndarray of int, shape (n,)
            Index of the containing triangle, ``-1`` outside the mesh.
        """
        pts = np.atleast_2d(np.asarray(points, dtype=float))[:, :2]
        out = np.full(len(pts), -1, dtype=np.int64)
        in_box = np.all(
            (pts >= self.bbox[0]) & (pts <= self.bbox[1]), axis=1
        )
        idx = np.nonzero(in_box)[0]
        if idx.size == 0:
            return out
        bi, bj = self._bucket(pts[idx])
        key = bi * self._shape[1] + bj
        order = np.argsort(key, kind="stable")
        idx, key = idx[order], key[order]
        buckets, first = np.unique(key, return_index=True)
        bounds = np.append(first, len(key))
        for b, s, e in zip(buckets, bounds[:-1], bounds[1:]):
            lo = self._bucket_start[b]
            hi = self._bucket_start[b + 1]
            tris = self._bucket_tris[lo:hi]
            if tris.size:
                out[idx[s:e]] = self._test(pts[idx[s:e]], tris)
        return out

    def _test(self, q: np.ndarray, tris: np.ndarray) -> np.ndarray:
        """Lowest-index triangle of *tris* containing each point."""
        d = q[:, None, :] - self._a[tris][None, :, :]
        det = self._det[tris][None, :]
        v0, v1 = self._v0[tris][None], self._v1[tris][None]
        with np.errstate(divide="ignore", invalid="ignore"):
            u = (d[..., 0] * v1[..., 1] - d[..., 1] * v1[..., 0]) / det
            v = (v0[..., 0] * d[..., 1] - v0[..., 1] * d[..., 0]) / det
        hit = (
            (u >= -_EPS)
            & (v >= -_EPS)
            & (u + v <= 1 + _EPS)
            & (det != 0)
        )
        big = np.iinfo(np.int64).max
        best = np.where(hit, tris[None, :], big).min(axis=1)
        return np.where(best == big, -1, best)


def locate_triangles(
    nodes: np.ndarray,
    connectivity: np.ndarray,
    points: np.ndarray,
) -> np.ndarray:
    """Index of the triangle containing each point.

    Parameters
    ----------
    nodes : array_like of shape (n_nodes, 2)
        Node coordinates.
    connectivity : array_like of int, shape (n_triangles, 3)
        Node indices of each triangle.
    points : array_like of shape (n, 2)
        Query points.

    Returns
    -------
    ndarray of int, shape (n,)
        Triangle index, ``-1`` for points outside the mesh.

    See Also
    --------
    TriangleLocator : Reusable locator for repeated queries.

    Examples
    --------
    >>> from pcsf.algorithms import locate_triangles
    >>> nodes = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
    >>> print(locate_triangles(nodes, [[0, 1, 2]], [[0.1, 0.1]]))
    [0]
    """
    return TriangleLocator(nodes, connectivity)(points)
