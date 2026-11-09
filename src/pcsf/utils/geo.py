"""Coordinate helpers.

:func:`transformer` needs the ``geo`` extra
(``pip install "pcsf[geo]"``); :func:`fit_affine` needs NumPy only.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..compat.optional import import_optional

__all__ = ["fit_affine", "transformer"]


def transformer(source: str, target: str) -> Any:
    """Coordinate transformer between two reference systems.

    Parameters
    ----------
    source, target : str
        CRS definitions accepted by pyproj, such as ``"EPSG:4326"``
        or ``"EPSG:32630"``.

    Returns
    -------
    pyproj.Transformer
        Transformer with ``always_xy=True``: coordinates are
        (easting or longitude, northing or latitude) whatever the
        axis order declared by the CRS.

    Raises
    ------
    MissingDependencyError
        If pyproj is not installed.

    Examples
    --------
    >>> from pcsf.utils.geo import transformer
    >>> t = transformer("EPSG:4326", "EPSG:32630")  # doctest: +SKIP
    >>> t.transform(-3.0, 0.0)  # doctest: +SKIP
    (500000.0, 0.0)
    """
    pyproj = import_optional(
        "pyproj", feature="coordinate transformations"
    )
    return pyproj.Transformer.from_crs(source, target, always_xy=True)


def fit_affine(
    u: np.ndarray, g: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Least-squares affine map between two 2-D point sets.

    Parameters
    ----------
    u : array_like of shape (n, 2)
        Points in the source frame, ``n >= 3`` and not collinear.
    g : array_like of shape (n, 2)
        The same points in the target frame.

    Returns
    -------
    A : ndarray of shape (2, 2)
        Linear part.
    b : ndarray of shape (2,)
        Translation.
    residual : ndarray of shape (n,)
        Euclidean misfit of each point, in the units of *g*.

    See Also
    --------
    pcsf.algorithms.register_frame : Frame registration built on it.

    Notes
    -----
    Solves :math:`\\min_{\\mathbf{A},\\mathbf{b}} \\sum_k
    \\|\\mathbf{A}\\mathbf{u}_k + \\mathbf{b} - \\mathbf{g}_k\\|^2`
    with :func:`numpy.linalg.lstsq` on the design matrix
    :math:`[\\mathbf{u}\\;\\mathbf{1}]`. Collinear points leave the
    problem rank-deficient; the minimum-norm solution is returned.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.utils.geo import fit_affine
    >>> u = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    >>> A, b, res = fit_affine(u, 2.0 * u + [5.0, -1.0])
    >>> print(np.round(A, 6) + 0.0, np.round(b, 6) + 0.0)
    [[2. 0.]
     [0. 2.]] [ 5. -1.]
    """
    u = np.asarray(u, dtype=float)
    g = np.asarray(g, dtype=float)
    design = np.column_stack([u, np.ones(len(u))])
    coef, *_ = np.linalg.lstsq(design, g, rcond=None)
    a, b = coef[:2].T, coef[2]
    residual = np.hypot(*(design @ coef - g).T)
    return a, b, residual
