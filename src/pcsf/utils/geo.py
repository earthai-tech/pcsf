"""Coordinate helpers (need the ``geo`` extra: ``pip install "pcsf[geo]"``)."""

from __future__ import annotations

import numpy as np

from ..compat.optional import import_optional

__all__ = ["fit_affine", "transformer"]


def transformer(source: str, target: str):
    """``pyproj.Transformer`` with (x, y) = (easting/longitude, northing/latitude) order."""
    pyproj = import_optional("pyproj", feature="coordinate transformations")
    return pyproj.Transformer.from_crs(source, target, always_xy=True)


def fit_affine(u: np.ndarray, g: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Least-squares affine map ``g = A u + b`` between two 2-D point sets.

    Parameters
    ----------
    u, g : ndarray, shape (n, 2)
        Corresponding points in the source and target frames (n >= 3).

    Returns
    -------
    A : ndarray (2, 2)
    b : ndarray (2,)
    residual : ndarray (n,)
        Euclidean residual of each point.
    """
    u = np.asarray(u, float)
    g = np.asarray(g, float)
    M = np.column_stack([u, np.ones(len(u))])
    coef, *_ = np.linalg.lstsq(M, g, rcond=None)
    A, b = coef[:2].T, coef[2]
    residual = np.hypot(*(M @ coef - g).T)
    return A, b, residual
