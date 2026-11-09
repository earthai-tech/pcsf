"""Algorithms on PCSF models, with NumPy as the only dependency.

Modules
-------
sampling
    Sampling operator :math:`\\mathcal{S}_M(\\mathbf{p})` and
    multilinear interpolation weights.
locate
    Point location in triangular meshes.
comparison
    Difference field and statistics :math:`\\varepsilon`,
    :math:`\\beta`, :math:`R`.
uncertainty
    Standard deviations and covariances under a change of encoding
    and through interpolation.
projection
    Node-to-cell projection of per-node resistivity.
registration
    Affine registration of a model frame and its decomposition.
regrid
    Synthesized ``grid2d`` export of a mesh model.
"""

from .comparison import ComparisonResult, compare_log10
from .locate import TriangleLocator, locate_triangles
from .projection import NODE_AVERAGES, node_to_cell
from .registration import (
    FrameRegistration,
    decompose_frame,
    register_frame,
)
from .regrid import mesh_to_grid2d
from .sampling import (
    InterpolationWeights,
    interpolation_weights,
    sample_log10,
)
from .uncertainty import (
    encoding_jacobian,
    interpolated_std,
    log_uncertainty,
    lognormal_relative_std,
    transform_covariance,
)

__all__ = [
    "NODE_AVERAGES",
    "ComparisonResult",
    "FrameRegistration",
    "InterpolationWeights",
    "TriangleLocator",
    "compare_log10",
    "decompose_frame",
    "encoding_jacobian",
    "interpolated_std",
    "interpolation_weights",
    "locate_triangles",
    "log_uncertainty",
    "lognormal_relative_std",
    "mesh_to_grid2d",
    "node_to_cell",
    "register_frame",
    "sample_log10",
    "transform_covariance",
]
