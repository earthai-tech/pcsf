"""Rectilinear export of a triangular-mesh model.

A mesh model stays a mesh in PCSF. When a consumer needs a
rectilinear approximation (a quick-look plot, a tool that reads only
grids), :func:`mesh_to_grid2d` samples the mesh on a regular grid by
point location. The result is labelled as synthesized so that it is
never mistaken for an inversion output.

See Also
--------
pcsf.algorithms.locate : Point location used here.
"""

from __future__ import annotations

import numpy as np

from ..core.schema import Grid2DGeometry, PCSFModel
from ..exceptions import GeometryError
from .locate import TriangleLocator

__all__ = ["mesh_to_grid2d"]

_NOTE = (
    "regridded from mesh_unstructured by point location "
    "(synthesized, not a native inversion output)"
)


def mesh_to_grid2d(
    model: PCSFModel,
    *,
    nx: int = 200,
    nz: int = 150,
) -> PCSFModel:
    """Sample a triangular-mesh model on a regular ``grid2d``.

    Parameters
    ----------
    model : PCSFModel
        Model of kind ``mesh_unstructured`` in plane ``"xz"`` with
        per-triangle resistivity of shape ``(n_triangles,)``. A
        per-region array must first be expanded onto each triangle's
        region id.
    nx, nz : int, default 200 and 150
        Number of grid points along x and z. A mesh has no natural
        rectilinear resolution, so these are explicit, bounded
        defaults.

    Returns
    -------
    PCSFModel
        New ``grid2d`` model with ``nz`` by ``nx`` cells spanning the
        mesh bounding box. Points outside the triangulation are NaN.
        ``source_backend``, ``created_by``, ``crs`` and ``survey`` are
        carried over; ``description`` and ``metadata`` (keys
        ``synthesized``, ``regridded_from``, ``regrid_nx``,
        ``regrid_nz``) record that the model is synthesized.

    Raises
    ------
    GeometryError
        If *model* is not ``mesh_unstructured``, its plane is not
        ``"xz"``, or its resistivity is not per triangle.

    See Also
    --------
    pcsf.algorithms.sample_log10 : Sample at arbitrary points.

    Notes
    -----
    Each grid point :math:`\\mathbf{p}_{ij}` takes the resistivity of
    the triangle :math:`t(\\mathbf{p}_{ij})` that contains it; no
    value is interpolated or extrapolated, so contrasts across region
    boundaries stay sharp at the cost of staircase edges of one grid
    step. The source values and the per-region table do not apply to
    the grid and are dropped.

    Examples
    --------
    >>> import numpy as np
    >>> import pcsf
    >>> from pcsf.algorithms import mesh_to_grid2d
    >>> geometry = pcsf.UnstructuredMeshGeometry(
    ...     nodes=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0],
    ...                     [1.0, 1.0]]),
    ...     connectivity=np.array([[0, 1, 2], [1, 3, 2]]),
    ...     region_ids=np.array([0, 1]),
    ... )
    >>> model = pcsf.PCSFModel(geometry=geometry,
    ...                        resistivity=np.array([10.0, 20.0]))
    >>> grid = mesh_to_grid2d(model, nx=5, nz=5)
    >>> grid.kind, grid.resistivity.shape
    ('grid2d', (5, 5))
    >>> grid.metadata["synthesized"]
    True
    """
    if model.kind != "mesh_unstructured":
        raise GeometryError(
            "mesh_to_grid2d expects a mesh_unstructured model, "
            f"got geometry kind {model.kind!r}"
        )
    geo = model.geometry
    if geo.plane != "xz":
        raise GeometryError(
            "mesh_to_grid2d supports plane='xz' meshes only, "
            f"got plane={geo.plane!r}"
        )
    connectivity = np.asarray(geo.connectivity, dtype=np.int64)
    n_tri = connectivity.shape[0]
    if model.resistivity.shape != (n_tri,):
        raise GeometryError(
            "mesh_to_grid2d needs per-triangle resistivity of shape "
            f"({n_tri},), got {model.resistivity.shape}; expand "
            "per-region values onto each triangle's region id first"
        )
    nodes = np.asarray(geo.nodes, dtype=float)
    resistivity = np.asarray(model.resistivity, dtype=float)
    x = np.linspace(nodes[:, 0].min(), nodes[:, 0].max(), nx)
    z = np.linspace(nodes[:, 1].min(), nodes[:, 1].max(), nz)
    x_grid, z_grid = np.meshgrid(x, z)  # both (nz, nx)
    points = np.column_stack([x_grid.ravel(), z_grid.ravel()])
    tri_idx = TriangleLocator(nodes, connectivity)(points)
    grid_rho = np.full(tri_idx.shape, np.nan)
    inside = tri_idx >= 0
    grid_rho[inside] = resistivity[tri_idx[inside]]
    if model.description:
        description = f"{model.description} -- {_NOTE}"
    else:
        description = _NOTE
    return PCSFModel(
        geometry=Grid2DGeometry(x=x, z=z),
        resistivity=grid_rho.reshape(nz, nx),
        source_backend=model.source_backend,
        created_by=model.created_by,
        crs=model.crs,
        description=description,
        survey=dict(model.survey),
        metadata={
            **model.metadata,
            "synthesized": True,
            "regridded_from": "mesh_unstructured",
            "regrid_nx": nx,
            "regrid_nz": nz,
        },
    )
