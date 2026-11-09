"""Registration of a model frame to projected coordinates.

A model frame and a projected system (easting E, northing N) are related by

.. math::

    \\mathbf{g} = \\mathbf{A}\\mathbf{u} + \\mathbf{b},\\qquad
    \\mathbf{A} = \\mathbf{R}(\\theta)\\,\\mathbf{S}\\,\\mathbf{P},

with :math:`\\mathbf{P}` an axis permutation (identity for east-first grids,
the swap for north-first grids such as ModEM's), :math:`\\mathbf{R}` a
rotation and :math:`\\mathbf{S}` scales. :func:`register_frame` estimates
:math:`\\mathbf{A}, \\mathbf{b}` by least squares from stations known in both
frames; :func:`decompose_frame` recovers :math:`\\mathbf{P}, \\theta, \\mathbf{S}`.
A negative determinant of :math:`\\mathbf{A}` reveals a permuted (north-first) frame.
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
    A, b : ndarray
        ``g = A u + b``.
    residual : ndarray
        Per-station residual (m).
    """

    A: np.ndarray
    b: np.ndarray
    residual: np.ndarray

    @property
    def rms_residual(self) -> float:
        return float(np.sqrt(np.mean(self.residual ** 2)))

    def __call__(self, u) -> np.ndarray:
        """Map projected points ``(n, 2)`` to the model frame."""
        return np.asarray(u, float) @ self.A.T + self.b


def register_frame(projected, model_frame) -> FrameRegistration:
    """Least-squares affine registration from >= 3 stations known in both frames."""
    A, b, res = fit_affine(projected, model_frame)
    return FrameRegistration(A, b, res)


def decompose_frame(A) -> dict:
    """Split ``A`` into permutation, rotation (degrees) and scales.

    Returns
    -------
    dict
        ``permuted`` (bool), ``P``, ``rotation_deg``, ``scales``, ``det``.
    """
    A = np.asarray(A, float)
    det = float(np.linalg.det(A))
    P = _SWAP if det < 0 else np.eye(2)
    B = A @ P.T
    U, s, Vt = np.linalg.svd(B)
    R = U @ Vt
    theta = float(np.degrees(np.arctan2(R[1, 0], R[0, 0])))
    return {"permuted": det < 0, "P": P, "rotation_deg": theta, "scales": s, "det": det}
