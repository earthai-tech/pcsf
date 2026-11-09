"""Uncertainty under a change of encoding and through resampling.

Three operations are provided:

* conversion of standard deviations between the ``log10``, ``ln``
  and ``linear`` encodings of resistivity
  (:func:`log_uncertainty`, :func:`lognormal_relative_std`);
* transformation of full covariance matrices
  (:func:`encoding_jacobian`, :func:`transform_covariance`);
* the standard deviation of multilinearly interpolated values
  (:func:`interpolated_std`).

Notes
-----
Let :math:`m = \\log_{10}\\rho` with :math:`\\rho` in ohm m. Between
the logarithmic encodings the conversion is linear and exact,
:math:`\\sigma_{\\ln\\rho} = \\ln(10)\\,\\sigma_m`. Toward linear
resistivity the first-order (delta-method) approximation is
:math:`\\sigma_\\rho \\approx \\rho\\ln(10)\\,\\sigma_m`. When
:math:`m` is Gaussian, :math:`\\rho` is log-normal and the delta
method underestimates its exact standard deviation by less than 1 %
for :math:`\\sigma_m \\le 0.05` decade, by about 15 % at 0.2 and by
about 64 % at 0.5 decade.

For a change of variables :math:`\\mathbf{y} = f(\\mathbf{m})` with
Jacobian
:math:`\\mathbf{J} = \\partial\\mathbf{y}/\\partial\\mathbf{m}`,

.. math::

    \\mathbf{C}_y \\approx \\mathbf{J}\\,\\mathbf{C}_m\\,\\mathbf{J}^T,

exact for the linear map between ``log10`` and ``ln``. An
interpolated value :math:`\\hat m(\\mathbf{p}) = \\mathbf{w}^T
\\mathbf{m}` has the exact variance
:math:`\\mathbf{w}^T\\mathbf{C}_m\\mathbf{w}`.
"""

from __future__ import annotations

import numpy as np

from ..exceptions import EncodingError
from .sampling import InterpolationWeights

__all__ = [
    "encoding_jacobian",
    "interpolated_std",
    "log_uncertainty",
    "lognormal_relative_std",
    "transform_covariance",
]

_LN10 = float(np.log(10.0))
_VALID = ("log10", "ln", "linear")


def _check_encodings(*names: str) -> None:
    """Raise EncodingError unless every name is a valid encoding."""
    bad = [n for n in names if n not in _VALID]
    if bad:
        raise EncodingError(
            f"encodings must be in {_VALID}, got {bad!r}"
        )


def log_uncertainty(
    sigma: np.ndarray,
    from_encoding: str,
    to_encoding: str = "log10",
    rho: np.ndarray | None = None,
) -> np.ndarray:
    """Convert a standard deviation of resistivity between encodings.

    Parameters
    ----------
    sigma : array_like
        Standard deviation in the source encoding: decades for
        ``"log10"``, nepers for ``"ln"``, ohm m for ``"linear"``.
    from_encoding : {"log10", "ln", "linear"}
        Encoding of *sigma*.
    to_encoding : {"log10", "ln", "linear"}, default "log10"
        Encoding of the result.
    rho : array_like, optional
        Resistivity (ohm m) at which a linear standard deviation is
        evaluated; required when either encoding is ``"linear"`` and
        broadcast against *sigma*.

    Returns
    -------
    ndarray of float
        Standard deviation in the target encoding.

    Raises
    ------
    EncodingError
        If an encoding is unknown, or *rho* is missing for a
        conversion to or from ``"linear"``.

    See Also
    --------
    lognormal_relative_std : Exact value of the linear spread.
    transform_covariance : Same conversion for covariance matrices.

    Notes
    -----
    With :math:`\\sigma_m` the standard deviation of
    :math:`m = \\log_{10}\\rho`,

    .. math::

        \\sigma_{\\ln\\rho} = \\ln(10)\\,\\sigma_m,\\qquad
        \\sigma_\\rho \\approx \\rho\\,\\ln(10)\\,\\sigma_m .

    The first relation is exact; the second is the delta method and
    underestimates the spread for large :math:`\\sigma_m`.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.algorithms import log_uncertainty
    >>> print(np.round(log_uncertainty([0.1], "log10", "ln"), 4))
    [0.2303]
    >>> s = log_uncertainty([0.1], "log10", "linear", rho=[100.0])
    >>> print(np.round(s, 2))
    [23.03]
    """
    _check_encodings(from_encoding, to_encoding)
    s = np.asarray(sigma, dtype=float)
    if "linear" in (from_encoding, to_encoding) and rho is None:
        raise EncodingError(
            "rho is required to convert to or from 'linear'"
        )
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


def lognormal_relative_std(sigma_log10: np.ndarray) -> np.ndarray:
    """Exact relative standard deviation of a log-normal resistivity.

    Parameters
    ----------
    sigma_log10 : array_like
        Standard deviation :math:`\\sigma_m` of
        :math:`m = \\log_{10}\\rho`, in decades.

    Returns
    -------
    ndarray of float
        Standard deviation of :math:`\\rho` divided by its median
        :math:`10^{\\mu_m}` (dimensionless).

    See Also
    --------
    log_uncertainty : First-order conversion.

    Notes
    -----
    If :math:`m \\sim \\mathcal{N}(\\mu_m, \\sigma_m^2)`, then
    :math:`\\ln\\rho \\sim \\mathcal{N}(\\ln(10)\\mu_m, s^2)` with
    :math:`s = \\ln(10)\\,\\sigma_m`, and

    .. math::

        \\frac{\\sigma_\\rho}{\\rho_{\\mathrm{med}}}
        = \\sqrt{\\left(e^{s^2} - 1\\right) e^{s^2}} .

    The delta method gives :math:`s` instead; the two agree to first
    order in :math:`s`.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.algorithms import lognormal_relative_std
    >>> print(np.round(lognormal_relative_std([0.05, 0.2]), 4))
    [0.1163 0.5404]
    """
    s = _LN10 * np.asarray(sigma_log10, dtype=float)
    return np.sqrt((np.exp(s * s) - 1.0) * np.exp(s * s))


def encoding_jacobian(
    rho: np.ndarray,
    from_encoding: str = "log10",
    to_encoding: str = "linear",
) -> np.ndarray:
    """Per-cell derivative of one encoding with respect to another.

    Parameters
    ----------
    rho : array_like
        Resistivity in ohm m at which the derivative is evaluated.
    from_encoding : {"log10", "ln", "linear"}, default "log10"
        Independent variable :math:`m`.
    to_encoding : {"log10", "ln", "linear"}, default "linear"
        Dependent variable :math:`y`.

    Returns
    -------
    ndarray of float
        :math:`\\mathrm{d}y/\\mathrm{d}m` with the shape of *rho*;
        the diagonal of the Jacobian, since each cell depends only on
        itself.

    Raises
    ------
    EncodingError
        If an encoding is unknown.

    See Also
    --------
    transform_covariance : Apply the Jacobian to a covariance.

    Notes
    -----
    By the chain rule,

    .. math::

        \\frac{\\mathrm{d}y}{\\mathrm{d}m} =
        \\frac{\\mathrm{d}\\rho/\\mathrm{d}m}
              {\\mathrm{d}\\rho/\\mathrm{d}y},\\qquad
        \\frac{\\mathrm{d}\\rho}{\\mathrm{d}\\log_{10}\\rho}
        = \\rho\\ln 10,\\quad
        \\frac{\\mathrm{d}\\rho}{\\mathrm{d}\\ln\\rho} = \\rho .

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.algorithms import encoding_jacobian
    >>> print(np.round(encoding_jacobian([100.0]), 2))
    [230.26]
    """
    _check_encodings(from_encoding, to_encoding)
    rho = np.asarray(rho, dtype=float)
    d_rho = {
        "log10": rho * _LN10,
        "ln": rho,
        "linear": np.ones_like(rho),
    }
    return d_rho[from_encoding] / d_rho[to_encoding]


def transform_covariance(
    cov: np.ndarray,
    rho: np.ndarray,
    from_encoding: str = "log10",
    to_encoding: str = "linear",
) -> np.ndarray:
    """Transform a covariance matrix to another encoding.

    Parameters
    ----------
    cov : array_like of shape (n, n)
        Covariance of the cells in *from_encoding*, cells flattened in
        C order.
    rho : array_like
        Resistivity in ohm m of the same ``n`` cells (any shape; it is
        flattened).
    from_encoding : {"log10", "ln", "linear"}, default "log10"
        Encoding of *cov*.
    to_encoding : {"log10", "ln", "linear"}, default "linear"
        Encoding of the result.

    Returns
    -------
    ndarray of float, shape (n, n)
        :math:`\\mathbf{C}_y = \\mathbf{J}\\mathbf{C}_m\\mathbf{J}^T`.

    Raises
    ------
    EncodingError
        If an encoding is unknown.

    See Also
    --------
    encoding_jacobian : Diagonal of :math:`\\mathbf{J}`.

    Notes
    -----
    Since :math:`\\mathbf{J} = \\mathrm{diag}(j_1, \\dots, j_n)`, the
    product is computed element-wise as
    :math:`(C_y)_{kl} = j_k (C_m)_{kl} j_l` in :math:`O(n^2)`. It is
    exact between ``log10`` and ``ln`` and first order otherwise.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.algorithms import transform_covariance
    >>> c = transform_covariance(np.diag([0.01]), [100.0])
    >>> print(np.round(c, 1))
    [[530.2]]
    """
    cov = np.asarray(cov, dtype=float)
    j = encoding_jacobian(np.ravel(rho), from_encoding, to_encoding)
    return (j[:, None] * cov) * j[None, :]


def interpolated_std(
    weights: InterpolationWeights,
    sigma: np.ndarray | None = None,
    cov: np.ndarray | None = None,
) -> np.ndarray:
    """Standard deviation of multilinearly interpolated values.

    Parameters
    ----------
    weights : InterpolationWeights
        Output of :func:`pcsf.algorithms.interpolation_weights`.
    sigma : array_like, optional
        Per-cell standard deviation with the model's resistivity
        shape, for uncorrelated cells.
    cov : array_like of shape (N, N), optional
        Full covariance over the ``N`` cells flattened in C order.

    Returns
    -------
    ndarray of float, shape (n,)
        Standard deviation at each point, in the units of *sigma* or
        *cov*; NaN outside the model.

    Raises
    ------
    ValueError
        Unless exactly one of *sigma* and *cov* is given.

    See Also
    --------
    pcsf.algorithms.interpolation_weights : Build *weights*.

    Notes
    -----
    For :math:`\\hat m = \\mathbf{w}^T\\mathbf{m}`,

    .. math::

        \\sigma^2(\\mathbf{p}) = \\mathbf{w}^T\\mathbf{C}_m\\mathbf{w}
        \\;\\overset{\\mathbf{C}_m\\,\\mathrm{diagonal}}{=}\\;
        \\sum_c w_c^2\\,\\sigma_c^2 ,

    exact for any covariance because the interpolation is linear.
    Small negative variances caused by rounding in a nearly singular
    covariance are clipped to zero.

    Examples
    --------
    >>> import numpy as np
    >>> import pcsf
    >>> from pcsf.algorithms import (interpolated_std,
    ...                              interpolation_weights)
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0, 10.0], z=[5.0]),
    ...     resistivity=[[10.0, 1000.0]],
    ... )
    >>> w = interpolation_weights(model, [[5.0, 5.0]])
    >>> s = interpolated_std(w, sigma=[[0.1, 0.1]])
    >>> print(np.round(s, 4))
    [0.0707]
    >>> s = interpolated_std(w, cov=np.full((2, 2), 0.01))
    >>> print(np.round(s, 4))
    [0.1]
    """
    if (sigma is None) == (cov is None):
        raise ValueError("give exactly one of sigma or cov")
    w, idx = weights.weights, weights.flat_index
    if sigma is not None:
        s = np.asarray(sigma, dtype=float).ravel()[idx]
        var = np.sum((w * s) ** 2, axis=1)
    else:
        c = np.asarray(cov, dtype=float)
        sub = c[idx[:, :, None], idx[:, None, :]]  # (n, K, K)
        var = np.einsum("nk,nkl,nl->n", w, sub, w)
    out = np.sqrt(np.maximum(var, 0.0))
    out[weights.outside] = np.nan
    return out
