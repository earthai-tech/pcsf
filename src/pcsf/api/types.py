"""Public type aliases used in pcsf signatures."""

from __future__ import annotations

import os
from typing import Literal, Union

import numpy as np
from numpy.typing import ArrayLike, NDArray

__all__ = [
    "ArrayLike",
    "Encoding",
    "FloatArray",
    "GeometryKind",
    "NodeAverage",
    "PathLike",
    "Termination",
]

PathLike = Union[str, "os.PathLike[str]"]
FloatArray = NDArray[np.float64]

#: Geometry kinds of the specification.
GeometryKind = Literal[
    "grid2d", "grid3d", "mesh_unstructured", "multiline"
]

#: Built-in encodings of source (native) values. Plugins may add others
#: through :func:`pcsf.api.registry.register_encoding`.
Encoding = Literal[
    "log10", "ln", "linear", "log10_conductivity", "conductivity"
]

#: Node-to-cell projections for per-node (graph) predictions.
NodeAverage = Literal["arithmetic", "geometric"]

#: How an inversion run ended (inversion record).
Termination = Literal[
    "target_reached",
    "iteration_limit",
    "time_limit",
    "stalled",
    "unknown",
]
