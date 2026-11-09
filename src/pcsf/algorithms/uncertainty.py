"""Uncertainty under a change of encoding and through resampling.

Standard deviations (diagonal)
    Between logarithmic encodings the conversion is exact,
    :math:`\\sigma_{\\ln\\rho} = \\ln(10)\\,\\sigma_m`. Toward linear
    resistivity the first-order (delta-method) approximation is
    :math:`\\sigma_\\rho \\approx \\rho\\ln(10)\\,\\sigma_m`; it underestimates
    the exact log-normal value by < 1 % for :math:`\\sigma_m \\le 0.05`
    decades but by 15 % at 0.2 and 64 % at 0.5 (:func:`lognormal_relative_std`).

Covariance matrices
    For a change of variables :math:`\\mathbf{y} = f(\\mathbf{m})` with
    Jacobian :math:`\\mathbf{J} = \\partial\\mathbf{y}/\\partial\\mathbf{m}`,
    :math:`\\mathbf{C}_y \\approx \\mathbf{J}\\,\\mathbf{C}_m\\,\\mathbf{J}^T`
    (exact for the linear maps between logarithmic encodings).

Resampling
    A multilinearly interpolated value :math:`\\hat m(\\mathbf{p}) = \\mathbf{w}^T\\mathbf{m}`
    has variance :math:`\\sigma^2(\\mathbf{p}) = \\mathbf{w}^T\\mathbf{C}_m\\mathbf{w}`,
    exact for any covariance; with uncorrelated cells it reduces to
    :math:`\\sum_c w_c^2 \\sigma_c^2`.
"""

from __future__ import annotations

import numpy as np

from ..exceptions import EncodingError
from .sampling import InterpolationWeights

__all__ = [
    "encoding_jacobian",
    "interpolated_std",
    "lognormal_relative_std",
    "log_uncertainty",
    "transform_covariance",
]

_LN10 = float(np.log(10.0))
_VALID = ("log10", "ln", "linear")


def log_uncertainty(sigma, from_encoding: str, to_encoding: str = "log10", rho=None):
    """Convert a standard deviation of resistivity between encodings.

    Exact between ``"log10"`` and ``"ln"``; first order to or from
    ``"linear"`` (needs *rho*).
    """
    s = np.asarray(sigma, dtype=float)
    if from_encoding not in _VALID or to_encoding not in _VALID:
        raise EncodingError(f"encodings must be in {_VALID}")
    if "linear" in (from_encoding, to_encoding) and rho is None:
        raise EncodingError("rho is required to convert to or from 'linear'")
    if from_encoding == "log10":
        s10 = s
    elif from_encoding == "ln":
        s10 = s / _LN10
    else:
        s10 = s / (np.asarray(rho, dtype=float) * _LN10)
    if to_encoding == "log10":
        return s10
    if to_encoding == "ln":
        return s10 * _LN10
    return np.asarray(rho, dtype=float) * _LN10 * s10


def lognormal_relative_std(sigma_log10) -> np.ndarray:
    """Exact relative standard deviation of a log-normal resistivity.

    :math:`\\sigma_\\rho/\\rho_{\\mathrm{med}} = \\sqrt{(e^{s^2}-1)e^{s^2}}`,
    :math:`s = \\ln(10)\\sigma_m`.
    """
    s = _LN10 * np.asarray(sigma_log10, dtype=float)
    return np.sqrt((np.exp(s * s) - 1.0) * np.exp(s * s))


def encoding_jacobian(rho, from_encoding: str = "log10", to_encoding: str = "linear") -> np.ndarray:
    """Diagonal of :math:`\\partial y/\\partial m` between two encodings, per cell."""
    rho = np.asarray(rho, dtype=float)
    d_lin = {"log10": rho * _LN10, "ln": rho, "linear": np.ones_like(rho)}
    if from_encoding not in _VALID or to_encoding not in _VALID:
        raise EncodingError(f"encodings must be in {_VALID}")
    # d(to)/d(from) = [d(to)/d(rho)] / [d(from)/d(rho)] = d_lin[from] / d_lin[to]
    return d_lin[from_encoding] / d_lin[to_encoding]


def transform_covariance(cov, rho, from_encoding: str = "log10",
                         to_encoding: str = "linear") -> np.ndarray:
    """:math:`\\mathbf{C}_y = \\mathbf{J}\\mathbf{C}_m\\mathbf{J}^T` for a full covariance matrix."""
    cov = np.asarray(cov, dtype=float)
    j = encoding_jacobian(np.ravel(rho), from_encoding, to_encoding)
    return (j[:, None] * cov) * j[None, :]


def interpolated_std(weights: InterpolationWeights, sigma=None, cov=None) -> np.ndarray:
    """Standard deviation of interpolated values, :math:`\\sqrt{\\mathbf{w}^T\\mathbf{C}\\mathbf{w}}`.

    Parameters
    ----------
    weights : InterpolationWeights
        From :func:`pcsf.algorithms.sampling.interpolation_weights`.
    sigma : array-like, optional
        Per-cell standard deviation (cells uncorrelated).
    cov : array-like, optional
        Full covariance matrix over the flattened cells.
    """
    if (sigma is None) == (cov is None):
        raise ValueError("give exactly one of sigma or cov")
    w, idx = weights.weights, weights.flat_index
    if sigma is not None:
        s = np.asarray(sigma, dtype=float).ravel()[idx]
        var = np.sum((w * s) ** 2, axis=1)
    else:
        c = np.asarray(cov, dtype=float)
        sub = c[idx[:, :, None], idx[:, None, :]]          # (n, k, k)
        var = np.einsum("nk,nkl,nl->n", w, sub, w)
    out = np.sqrt(np.maximum(var, 0.0))
    out[weights.outside] = np.nan
    return out
