"""Comparison statistics of two sampled log-resistivity fields.

See Also
--------
pcsf.algorithms.sample_log10 : Sample two models at common points.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..exceptions import GeometryError

__all__ = ["ComparisonResult", "compare_log10"]


@dataclass
class ComparisonResult:
    """Difference field and its summary statistics.

    Attributes
    ----------
    delta : ndarray of float
        Point-wise difference :math:`\\Delta_k` (decades); NaN where
        either field is undefined.
    rms : float
        Root-mean-square difference :math:`\\varepsilon` (decades).
    bias : float
        Mean difference :math:`\\beta` (decades); positive when the
        first field is the more resistive.
    correlation : float
        Pearson correlation :math:`R` of the two fields; NaN when
        either field is constant or fewer than two points remain.
    n : int
        Number of points where both fields are defined.

    See Also
    --------
    compare_log10 : Build a result from two sampled fields.

    Examples
    --------
    >>> from pcsf.algorithms import compare_log10
    >>> res = compare_log10([1.0, 2.0], [1.0, 2.5])
    >>> stats = res.as_dict()
    >>> round(stats["rms"], 4), stats["bias"], stats["n"]
    (0.3536, -0.25, 2)
    """

    delta: np.ndarray
    rms: float
    bias: float
    correlation: float
    n: int

    def as_dict(self) -> dict:
        """Summary statistics as a plain dictionary.

        Returns
        -------
        dict
            Keys ``rms``, ``bias``, ``correlation`` and ``n``.
        """
        return {
            "rms": self.rms,
            "bias": self.bias,
            "correlation": self.correlation,
            "n": self.n,
        }


def compare_log10(log_a, log_b) -> ComparisonResult:
    """Compare two log10 resistivity fields sampled at the same points.

    Parameters
    ----------
    log_a, log_b : array_like
        :math:`\\log_{10}\\rho` of two models at the same points, any
        but equal shapes; NaN marks undefined values.

    Returns
    -------
    ComparisonResult
        Difference field and statistics over the points where both
        fields are finite.

    Raises
    ------
    GeometryError
        If the two inputs have different shapes.

    See Also
    --------
    pcsf.algorithms.sample_log10 : Sample models at common points.

    Notes
    -----
    Over the :math:`N` points where both fields are defined,

    .. math::

        \\Delta_k = a_k - b_k,\\qquad
        \\varepsilon =
        \\Big[\\frac{1}{N}\\sum_k \\Delta_k^2\\Big]^{1/2},
        \\qquad
        \\beta = \\frac{1}{N}\\sum_k \\Delta_k,

    and :math:`R` is the Pearson correlation of :math:`a` and
    :math:`b`. :math:`\\varepsilon` and :math:`\\beta` are in decades;
    :math:`R` tells whether the two models place structures at the
    same positions regardless of their absolute level. With no
    common point, all statistics are NaN and ``n`` is zero.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.algorithms import compare_log10
    >>> res = compare_log10([1.0, 2.0, np.nan, 4.0],
    ...                     [1.5, 2.0, 3.0, 4.5])
    >>> res.n, round(res.bias, 4)
    (3, -0.3333)
    """
    a = np.asarray(log_a, dtype=float)
    b = np.asarray(log_b, dtype=float)
    if a.shape != b.shape:
        raise GeometryError(f"shape mismatch: {a.shape} vs {b.shape}")
    delta = a - b
    valid = np.isfinite(delta)
    n = int(valid.sum())
    if n == 0:
        return ComparisonResult(delta, np.nan, np.nan, np.nan, 0)
    d = delta[valid]
    if n > 1 and np.std(a[valid]) > 0 and np.std(b[valid]) > 0:
        r = float(np.corrcoef(a[valid], b[valid])[0, 1])
    else:
        r = float("nan")
    return ComparisonResult(
        delta,
        float(np.sqrt(np.mean(d * d))),
        float(np.mean(d)),
        r,
        n,
    )
