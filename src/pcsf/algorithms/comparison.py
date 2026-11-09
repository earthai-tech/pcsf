"""Comparison of two sampled log-resistivity fields.

.. math::

    \\Delta_k = \\mathcal{S}_A(\\mathbf{p}_k) - \\mathcal{S}_B(\\mathbf{p}_k),\\quad
    \\varepsilon = \\Big[\\tfrac{1}{N}\\sum_k \\Delta_k^2\\Big]^{1/2},\\quad
    \\beta = \\tfrac{1}{N}\\sum_k \\Delta_k,\\quad
    R = \\operatorname{corr}(\\mathcal{S}_A, \\mathcal{S}_B)

over the N points where both fields are defined.
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
    delta : ndarray
        Point-wise difference (NaN where either field is undefined).
    rms : float
        Root-mean-square difference :math:`\\varepsilon` (decades).
    bias : float
        Mean difference :math:`\\beta` (decades).
    correlation : float
        Pearson correlation :math:`R` of the two fields.
    n : int
        Number of points where both fields are defined.
    """

    delta: np.ndarray
    rms: float
    bias: float
    correlation: float
    n: int

    def as_dict(self) -> dict:
        return {"rms": self.rms, "bias": self.bias, "correlation": self.correlation, "n": self.n}


def compare_log10(log_a, log_b) -> ComparisonResult:
    """Compare two :math:`\\log_{10}\\rho` fields sampled at the same points."""
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
        r = np.nan
    return ComparisonResult(delta, float(np.sqrt(np.mean(d * d))), float(np.mean(d)), r, n)
