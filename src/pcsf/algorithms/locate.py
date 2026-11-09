"""Point location in a triangular mesh (NumPy only).

:func:`locate_triangles` returns, for each query point, the index of the
triangle that contains it, or ``-1``. Triangles are first binned on a
regular grid of buckets over the mesh bounding box; each point is then
tested only against the triangles of its bucket with barycentric
coordinates. With about one triangle per bucket the cost is
O(m + n) for m triangles and n points.

A point on an edge shared by two triangles is assigned to the one with
the lower index, so that the result is deterministic.
"""

from __future__ import annotations

import numpy as np

__all__ = ["TriangleLocator", "locate_triangles"]

_EPS = 1e-12


class TriangleLocator:
    """Reusable locator for one mesh.

    Parameters
    ----------
    nodes : array-like, shape (n, 2)
        Node coordinates.
    connectivity : array-like, shape (m, 3)
        Triangle node indices.
    bucket_size : float, optional
        Target number of triangles per bucket (default 2).
    """

    def __init__(self, nodes, connectivity, *, bucket_size: float = 2.0) -> None:
        self.nodes = np.asarray(nodes, dtype=float)[:, :2]
        self.tri = np.asarray(connectivity, dtype=np.int64)
        P = self.nodes[self.tri]                         # (m, 3, 2)
        self._a = P[:, 0]
        self._v0 = P[:, 1] - P[:, 0]
        self._v1 = P[:, 2] - P[:, 0]
        self._det = self._v0[:, 0] * self._v1[:, 1] - self._v0[:, 1] * self._v1[:, 0]
        lo, hi = P.min(axis=1), P.max(axis=1)            # triangle bounding boxes
        self._lo, self._hi = lo, hi
        self.bbox = (lo.min(axis=0), hi.max(axis=0))
        m = len(self.tri)
        # buckets: roughly square, about bucket_size triangles each
        span = np.maximum(self.bbox[1] - self.bbox[0], _EPS)
        n_b = max(1, int(np.sqrt(m / max(bucket_size, 1e-9))))
        aspect = span[0] / span[1]
        nx = max(1, int(round(n_b * np.sqrt(aspect))))
        ny = max(1, int(round(n_b / np.sqrt(aspect))))
        self._shape = (nx, ny)
        self._cell = span / np.array([nx, ny])
        i0, j0 = self._bucket(lo)
        i1, j1 = self._bucket(hi)
        # triangles covering many buckets (large padding cells) are expanded
        counts = (i1 - i0 + 1) * (j1 - j0 + 1)
        tri_ids = np.repeat(np.arange(m), counts)
        offs = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
        width = np.repeat(i1 - i0 + 1, counts)
        bi = np.repeat(i0, counts) + offs % width
        bj = np.repeat(j0, counts) + offs // width
        key = bi * ny + bj
        order = np.argsort(key, kind="stable")
        self._bucket_tris = tri_ids[order]
        self._bucket_start = np.searchsorted(key[order], np.arange(nx * ny + 1))

    def _bucket(self, xy: np.ndarray):
        ij = np.floor((xy - self.bbox[0]) / self._cell).astype(np.int64)
        return (np.clip(ij[..., 0], 0, self._shape[0] - 1),
                np.clip(ij[..., 1], 0, self._shape[1] - 1))

    def __call__(self, points) -> np.ndarray:
        """Triangle index of each point (``-1`` outside the mesh)."""
        pts = np.atleast_2d(np.asarray(points, dtype=float))[:, :2]
        out = np.full(len(pts), -1, dtype=np.int64)
        inside_box = np.all((pts >= self.bbox[0]) & (pts <= self.bbox[1]), axis=1)
        idx = np.nonzero(inside_box)[0]
        if idx.size == 0:
            return out
        bi, bj = self._bucket(pts[idx])
        key = bi * self._shape[1] + bj
        order = np.argsort(key, kind="stable")
        idx, key = idx[order], key[order]
        uniq, first = np.unique(key, return_index=True)
        bounds = np.append(first, len(key))
        for b, s, e in zip(uniq, bounds[:-1], bounds[1:]):
            tris = self._bucket_tris[self._bucket_start[b]:self._bucket_start[b + 1]]
            if tris.size == 0:
                continue
            q = pts[idx[s:e]]                                    # (k, 2)
            d = q[:, None, :] - self._a[tris][None, :, :]        # (k, t, 2)
            det = self._det[tris][None, :]
            v0, v1 = self._v0[tris][None], self._v1[tris][None]
            with np.errstate(divide="ignore", invalid="ignore"):
                u = (d[..., 0] * v1[..., 1] - d[..., 1] * v1[..., 0]) / det
                v = (v0[..., 0] * d[..., 1] - v0[..., 1] * d[..., 0]) / det
            hit = (u >= -_EPS) & (v >= -_EPS) & (u + v <= 1 + _EPS) & (det != 0)
            any_hit = hit.any(axis=1)
            first_hit = np.argmax(hit, axis=1)                   # lowest-index triangle
            cand = np.where(any_hit, tris[first_hit], -1)
            # among hits, prefer the lowest triangle index for determinism
            if hit.sum(axis=1).max(initial=0) > 1:
                masked = np.where(hit, tris[None, :], np.iinfo(np.int64).max)
                cand = np.where(any_hit, masked.min(axis=1), -1)
            out[idx[s:e]] = cand
        return out


def locate_triangles(nodes, connectivity, points) -> np.ndarray:
    """Index of the triangle containing each point (``-1`` outside)."""
    return TriangleLocator(nodes, connectivity)(points)
