"""Registration of a model frame to projected coordinates.

Inversion codes often work in a local frame whose origin, rotation
and axis order differ from the projected coordinates of the survey.
This module estimates the affine map between the two frames from
stations known in both, and splits it into interpretable parts.

Notes
-----
With :math:`\\mathbf{u}` the projected coordinates (easting,
northing) and :math:`\\mathbf{g}` the model-frame coordinates of the
same point, both in metres,

.. math::

    \\mathbf{g} = \\mathbf{A}\\mathbf{u} + \\mathbf{b},\\qquad
    \\mathbf{A} = \\mathbf{R}(\\theta)\\,\\mathbf{S}\\,\\mathbf{P},

where :math:`\\mathbf{P}` is the identity for east-first frames or
the axis swap for north-first frames (as in ModEM),
:math:`\\mathbf{R}(\\theta)` a rotation by :math:`\\theta`
counter-clockwise, :math:`\\mathbf{S}` a diagonal matrix of positive
scales and :math:`\\mathbf{b}` a translation.
:func:`register_frame` estimates :math:`\\mathbf{A}` and
:math:`\\mathbf{b}`; :func:`decompose_frame` recovers
:math:`\\mathbf{P}`, :math:`\\theta` and :math:`\\mathbf{S}`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..utils.geo import fit_affine

__all__ = ["FrameRegistration", "decompose_frame", "register_frame"]

_SWAP = np.array([[0.0, 1.0], [1.0, 0.0]])


@dataclass
class FrameRegistration:
    """Affine map from projected to model-frame coordinates.

    Attributes
    ----------
    A : ndarray of shape (2, 2)
        Linear part of the map, :math:`\\mathbf{A}`.
    b : ndarray of shape (2,)
        Translation :math:`\\mathbf{b}`, in metres.
    residual : ndarray of shape (n,)
        Euclidean misfit of each station after the fit, in metres.

    See Also
    --------
    register_frame : Estimate the registration.
    decompose_frame : Interpret :attr:`A`.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.algorithms import FrameRegistration
    >>> reg = FrameRegistration(np.eye(2), np.array([10.0, 0.0]),
    ...                         np.zeros(3))
    >>> print(reg([[1.0, 2.0]]))
    [[11.  2.]]
    """

    A: np.ndarray
    b: np.ndarray
    residual: np.ndarray

    @property
    def rms_residual(self) -> float:
        """Root-mean-square station misfit, in metres."""
        return float(np.sqrt(np.mean(self.residual**2)))

    def __call__(self, u: np.ndarray) -> np.ndarray:
        """Map projected points to the model frame.

        Parameters
        ----------
        u : array_like of shape (n, 2)
            Projected coordinates (easting, northing) in metres.

        Returns
        -------
        ndarray of shape (n, 2)
            Model-frame coordinates :math:`\\mathbf{A}\\mathbf{u} +
            \\mathbf{b}`.
        """
        return np.asarray(u, dtype=float) @ self.A.T + self.b


def register_frame(
    projected: np.ndarray, model_frame: np.ndarray
) -> FrameRegistration:
    """Estimate the affine map from projected to model coordinates.

    Parameters
    ----------
    projected : array_like of shape (n, 2)
        Station coordinates (easting, northing) in metres, ``n >= 3``
        and not collinear.
    model_frame : array_like of shape (n, 2)
        Coordinates of the same stations in the model frame.

    Returns
    -------
    FrameRegistration
        Fitted map and per-station residuals.

    See Also
    --------
    decompose_frame : Split the fitted :math:`\\mathbf{A}`.
    pcsf.utils.geo.fit_affine : Underlying least-squares fit.

    Notes
    -----
    The six unknowns of :math:`\\mathbf{A}` and :math:`\\mathbf{b}`
    minimise :math:`\\sum_k \\|\\mathbf{A}\\mathbf{u}_k + \\mathbf{b}
    - \\mathbf{g}_k\\|^2` by linear least squares. A root-mean-square
    residual well above the station-location accuracy means the two
    frames are not related by an affine map (for instance a
    topography-following mesh or a wrong station list).

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.algorithms import register_frame
    >>> u = np.array([[0.0, 0.0], [100.0, 0.0], [0.0, 100.0]])
    >>> g = u[:, ::-1] + [10.0, 20.0]  # north-first frame
    >>> reg = register_frame(u, g)
    >>> print(np.round(reg.A, 6) + 0.0)
    [[0. 1.]
     [1. 0.]]
    """
    a, b, res = fit_affine(projected, model_frame)
    return FrameRegistration(a, b, res)


def decompose_frame(A: np.ndarray) -> dict:
    """Split a registration matrix into permutation, rotation, scales.

    Parameters
    ----------
    A : array_like of shape (2, 2)
        Linear part of a frame registration, as in
        :attr:`FrameRegistration.A`.

    Returns
    -------
    dict
        ``permuted`` (bool)
            True when the model frame is north-first.
        ``P`` (ndarray of shape (2, 2))
            Axis permutation :math:`\\mathbf{P}`.
        ``rotation_deg`` (float)
            :math:`\\theta` in degrees, counter-clockwise, in
            :math:`(-180, 180]`.
        ``scales`` (ndarray of shape (2,))
            Singular values of :math:`\\mathbf{A}\\mathbf{P}^T`, in
            decreasing order (not per axis).
        ``det`` (float)
            :math:`\\det\\mathbf{A}`.

    See Also
    --------
    register_frame : Estimate :math:`\\mathbf{A}`.

    Notes
    -----
    Rotations and positive scales have positive determinant and the
    swap has :math:`\\det\\mathbf{P} = -1`, so the sign of
    :math:`\\det\\mathbf{A}` reveals the axis order. With
    :math:`\\mathbf{B} = \\mathbf{A}\\mathbf{P}^T =
    \\mathbf{R}\\mathbf{S}` and the singular value decomposition
    :math:`\\mathbf{B} =
    \\mathbf{U}\\boldsymbol{\\Sigma}\\mathbf{V}^T`,
    the rotation is the polar factor
    :math:`\\mathbf{R} = \\mathbf{U}\\mathbf{V}^T` and the scales are
    the diagonal of :math:`\\boldsymbol{\\Sigma}`. The decomposition
    is exact for diagonal :math:`\\mathbf{S}`; for a general affine
    map with shear it returns the closest rotation in the Frobenius
    norm.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.algorithms import decompose_frame
    >>> t = np.radians(30.0)
    >>> R = np.array([[np.cos(t), -np.sin(t)],
    ...               [np.sin(t), np.cos(t)]])
    >>> d = decompose_frame(R @ [[0.0, 1.0], [1.0, 0.0]])
    >>> d["permuted"], round(d["rotation_deg"], 6)
    (True, 30.0)
    """
    a = np.asarray(A, dtype=float)
    det = float(np.linalg.det(a))
    p = _SWAP if det < 0 else np.eye(2)
    u, s, vt = np.linalg.svd(a @ p.T)
    r = u @ vt
    theta = float(np.degrees(np.arctan2(r[1, 0], r[0, 0])))
    return {
        "permuted": det < 0,
        "P": p,
        "rotation_deg": theta,
        "scales": s,
        "det": det,
    }
