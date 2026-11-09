"""Algorithms on PCSF models (NumPy only).

- :mod:`pcsf.algorithms.sampling`     -- :math:`\\mathcal{S}_M(\\mathbf{p})`, interpolation weights
- :mod:`pcsf.algorithms.locate`       -- point location in triangular meshes
- :mod:`pcsf.algorithms.comparison`   -- :math:`\\Delta, \\varepsilon, \\beta, R`
- :mod:`pcsf.algorithms.uncertainty`  -- encodings, covariance, resampling variance
- :mod:`pcsf.algorithms.projection`   -- node-to-cell projection
- :mod:`pcsf.algorithms.registration` -- frame registration and decomposition
- :mod:`pcsf.algorithms.regrid`       -- mesh to grid (synthesized export)
"""

from .comparison import ComparisonResult, compare_log10
from .locate import TriangleLocator, locate_triangles
from .projection import NODE_AVERAGES, node_to_cell
from .registration import FrameRegistration, decompose_frame, register_frame
from .regrid import mesh_to_grid2d
from .sampling import InterpolationWeights, interpolation_weights, sample_log10
from .uncertainty import (
    encoding_jacobian,
    interpolated_std,
    log_uncertainty,
    lognormal_relative_std,
    transform_covariance,
)

__all__ = [
    "NODE_AVERAGES", "ComparisonResult", "FrameRegistration", "InterpolationWeights",
    "TriangleLocator", "compare_log10", "decompose_frame", "encoding_jacobian",
    "interpolated_std", "interpolation_weights", "locate_triangles", "log_uncertainty",
    "lognormal_relative_std", "mesh_to_grid2d", "node_to_cell", "register_frame",
    "sample_log10", "transform_covariance",
]
