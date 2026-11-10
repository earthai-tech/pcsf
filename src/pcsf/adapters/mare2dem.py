"""MARE2DEM files to a ``mesh_unstructured`` PCSF model.

See Also
--------
pcsf.native.mare2dem : Parsers of the individual files.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import numpy as np

from ..api.registry import register_adapter
from ..core.schema import PCSFModel, UnstructuredMeshGeometry
from ..exceptions import AdapterError, GeometryError
from ..native import mare2dem as native
from ._common import survey_dict

__all__ = ["expand_regions", "mare2dem_to_pcsf"]

_ITER_NAME = re.compile(r"\.(\d+)\.resistivity$", re.IGNORECASE)


def expand_regions(
    rho_by_region: np.ndarray, region_ids: np.ndarray
) -> np.ndarray:
    """Resistivity of each triangle from the per-region table.

    Parameters
    ----------
    rho_by_region : array_like of shape (n_regions,)
        Row ``i`` holds region ``i``.
    region_ids : array_like of int, shape (n_triangles,)
        0-based region index of each triangle, as stored in PCSF
        (specification, mesh geometry).

    Returns
    -------
    ndarray of shape (n_triangles,)
        ``rho_by_region[region_ids]``.

    Raises
    ------
    GeometryError
        If a region index is outside ``[0, n_regions)``.

    Examples
    --------
    >>> from pcsf.adapters.mare2dem import expand_regions
    >>> expand_regions([10.0, 100.0], [1, 0, 1]).tolist()
    [100.0, 10.0, 100.0]
    """
    table = np.asarray(rho_by_region, dtype=float)
    ids = np.asarray(region_ids, dtype=np.int64)
    if ids.size and (ids.min() < 0 or ids.max() >= table.shape[0]):
        raise GeometryError(
            f"region ids span [{ids.min()}, {ids.max()}], outside "
            f"[0, {table.shape[0]})"
        )
    return table[ids]


@register_adapter("mare2dem")
def mare2dem_to_pcsf(
    resistivity: str | os.PathLike[str],
    *,
    poly: str | os.PathLike[str] | None = None,
    mesh: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None,
    log: str | os.PathLike[str] | None = None,
    survey: Any = None,
    created_by: str = "",
    crs: str | None = None,
    description: str = "",
) -> PCSFModel:
    """Convert a MARE2DEM result to a ``mesh_unstructured`` model.

    Parameters
    ----------
    resistivity : str or os.PathLike
        ``.resistivity`` file of the iteration to convert.
    poly : str or os.PathLike, optional
        ``.poly`` model file, triangulated with Triangle
        (``pcsf[mare2dem]``); by default the ``Model File`` named
        in the resistivity header, next to it.
    mesh : tuple of ndarray, optional
        ``(nodes, triangles, region_ids)`` of an existing
        triangulation, used instead of *poly*: nodes ``(n, 2)`` in
        metres, 0-based triangles ``(m, 3)``, and region numbers
        ``(m,)`` in MARE2DEM's own numbering, from 1.
    log : str or os.PathLike, optional
        MARE2DEM log file, for the iteration history.
    survey : mapping or object, optional
        Survey metadata.
    created_by, crs, description : str, optional
        Stored in the model.

    Returns
    -------
    PCSFModel
        Per-triangle resistivity in ohm m, the per-region table,
        history when a log is given, and metadata
        ``resistivity_file``, ``final_rms``, ``n_iterations``,
        ``converged``, ``n_regions`` and ``anisotropy``.

    Raises
    ------
    AdapterError
        If the model is anisotropic or no mesh can be obtained.
    GeometryError
        If the mesh refers to regions the table does not have.
    MissingDependencyError
        If triangulation is needed and Triangle is not installed.

    See Also
    --------
    expand_regions
    pcsf.native.mare2dem : File parsers.

    Notes
    -----
    The mesh is kept as is, never regridded; node coordinates are
    MARE2DEM's :math:`(y, z)`, stored with plane ``"xz"``. Only
    isotropic models are supported.

    Examples
    --------
    >>> import numpy as np
    >>> import pcsf
    >>> from pcsf.adapters import mare2dem_to_pcsf
    >>> run = pcsf.datasets.path("mare2dem_tiny")
    >>> nodes = np.loadtxt(run / "tiny.node.txt")
    >>> tri = np.loadtxt(run / "tiny.ele.txt", dtype=int)
    >>> model = mare2dem_to_pcsf(
    ...     run / "tiny.1.resistivity",
    ...     mesh=(nodes, tri[:, :3], tri[:, 3]),
    ...     log=run / "tiny.logfile",
    ... )
    >>> model.kind, model.resistivity.shape
    ('mesh_unstructured', (4,))
    """
    res_path = Path(resistivity)
    table = native.read_resistivity(res_path)
    if table.anisotropy != "isotropic":
        raise AdapterError(
            "only isotropic MARE2DEM models are supported, got "
            f"{table.anisotropy!r}"
        )
    if mesh is None:
        if poly is None:
            name = table.header.get("MODEL FILE", "")
            if not name:
                raise AdapterError(
                    f"{res_path}: no Model File; pass poly or mesh"
                )
            poly = res_path.parent / Path(name).name
        nodes, triangles, region_ids = native.triangulate_poly(
            native.read_poly(poly)
        )
    else:
        nodes, triangles, region_ids = (np.asarray(a) for a in mesh)
    # MARE2DEM numbers regions from 1; PCSF stores 0-based indices
    # into the per-region table, converted once here.
    region_ids = np.asarray(region_ids, dtype=np.int64) - 1
    by_region = np.asarray(table.rho[:, 0], dtype=float)
    m = _ITER_NAME.search(res_path.name)
    geometry = UnstructuredMeshGeometry(
        nodes=nodes,
        connectivity=triangles,
        region_ids=region_ids,
        plane="xz",
    )
    metadata: dict[str, Any] = {
        "resistivity_file": res_path.name,
        "iteration": int(m.group(1)) if m else -1,
        "n_regions": int(by_region.size),
        "anisotropy": table.anisotropy,
    }
    history: dict[str, np.ndarray] = {}
    if log is not None:
        lg = native.read_log(log)
        history = {
            "iteration": lg.iteration.astype(float),
            "rms": lg.rms,
            "roughness": lg.roughness,
            "lambda": lg.mu,
        }
        metadata.update(
            final_rms=float(lg.rms[-1]) if lg.rms.size else None,
            n_iterations=int(lg.iteration.size),
            converged=lg.converged,
        )
    return PCSFModel(
        geometry=geometry,
        resistivity=expand_regions(by_region, region_ids),
        resistivity_by_region=by_region,
        survey=survey_dict(survey),
        history=history,
        source_backend="mare2dem",
        created_by=created_by,
        crs=crs,
        description=description,
        metadata=metadata,
    )
