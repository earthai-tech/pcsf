"""Occam2D run folder to a ``grid2d`` PCSF model.

See Also
--------
pcsf.native.occam2d : Parsers of the individual files.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from ..api.registry import register_adapter
from ..core.schema import Grid2DGeometry, PCSFModel
from ..exceptions import AdapterError
from ..native import occam2d as native
from ..native._tokens import file_number
from ._common import station_table, survey_dict

__all__ = ["chainage_shift", "occam2d_to_pcsf"]


def chainage_shift(x_nodes: np.ndarray, offsets: np.ndarray) -> float:
    """Shift from mesh coordinates to station chainage.

    Parameters
    ----------
    x_nodes : array_like of shape (n_x + 1,)
        Mesh column edges, starting at the outer edge of the left
        padding.
    offsets : array_like of shape (n_sites,)
        Station offsets from the data file.

    Returns
    -------
    float
        Value added to mesh coordinates; 0 with fewer than two
        stations.

    Notes
    -----
    Occam2D meshes measure :math:`x` from the outer edge of the
    padding, whereas station offsets are chainage. With padding of
    equal width on both sides, the station core is centred in the
    mesh, so

    .. math::

        s = \\min_k o_k - \\Big(x_0 + \\frac{(x_N - x_0) -
        (\\max_k o_k - \\min_k o_k)}{2}\\Big),

    without assuming a number of padding cells. Meshes with
    asymmetric padding need an explicit correction.

    Examples
    --------
    >>> from pcsf.adapters.occam2d import chainage_shift
    >>> chainage_shift([0.0, 100.0, 150.0, 200.0, 300.0],
    ...                [0.0, 100.0])
    -100.0
    """
    o = np.asarray(offsets, dtype=float)
    n = np.asarray(x_nodes, dtype=float)
    if o.size < 2:
        return 0.0
    pad = ((n[-1] - n[0]) - (o.max() - o.min())) / 2.0
    return float(o.min() - (n[0] + pad))


def _pick_iteration(wd: Path, iteration: int | None) -> Path:
    files = sorted(wd.glob("*.iter"), key=file_number)
    if not files:
        raise AdapterError(f"{wd}: no Occam2D *.iter file")
    if iteration is None:
        return files[-1]
    for f in files:
        if file_number(f) == iteration:
            return f
    raise AdapterError(f"{wd}: no iteration file for {iteration}")


def _find_log(wd: Path) -> Path | None:
    for pattern in ("*.logfile", "LogFile*"):
        found = sorted(wd.glob(pattern))
        if found:
            return found[0]
    return None


def _named(wd: Path, name: str, what: str) -> Path:
    path = wd / Path(name).name
    if not name or not path.is_file():
        raise AdapterError(f"{wd}: {what} file {name!r} not found")
    return path


@register_adapter("occam2d")
def occam2d_to_pcsf(
    workdir: str | os.PathLike[str],
    *,
    iteration: int | None = None,
    station_lonlat: Mapping[str, tuple[float, float]] | None = None,
    station_elevations: Mapping[str, float] | None = None,
    survey: Any = None,
    origin: Sequence[float] | None = None,
    azimuth_deg: float | None = None,
    created_by: str = "",
    crs: str | None = None,
    description: str = "",
) -> PCSFModel:
    """Convert an Occam2D run folder to a ``grid2d`` model.

    Parameters
    ----------
    workdir : str or os.PathLike
        Folder with the iteration, model, mesh and data files and,
        optionally, the log file.
    iteration : int, optional
        Iteration to convert; the highest-numbered ``*.iter`` file
        by default.
    station_lonlat : mapping of str to (lon, lat), optional
        WGS84 station positions; Occam2D files have none.
    station_elevations : mapping of str to float, optional
        Station elevations in metres; Occam2D files have none. They
        become the station ``z`` and the topography; unknown
        elevations are NaN.
    survey : mapping or object, optional
        Survey metadata, stored as a dictionary.
    origin : sequence of float, optional
        Real-world ``(x, y)`` of the profile origin.
    azimuth_deg : float, optional
        Profile bearing.
    created_by, crs, description : str, optional
        Stored in the model.

    Returns
    -------
    PCSFModel
        Linear resistivity in ohm m with the log10 values of the
        iteration kept as source values (encoding ``log10``), station
        table, iteration history from the log file, and metadata
        ``workdir``, ``iteration_file``, ``final_rms``,
        ``n_iterations`` and, with a log, ``converged``.

    Raises
    ------
    AdapterError
        If the folder lacks an iteration file or a file it names.
    FormatError
        If a file is malformed.

    See Also
    --------
    chainage_shift : Recovery of the station chainage.
    pcsf.native.occam2d : File parsers.

    Notes
    -----
    Files are located through the names each file records: the
    iteration file names the model and data files, and the model
    file names the mesh file. The horizontal coordinates are shifted
    by :func:`chainage_shift` so that cells and stations share the
    chainage of the data file.

    Examples
    --------
    >>> import pcsf
    >>> from pcsf.adapters import occam2d_to_pcsf
    >>> run = pcsf.datasets.path("occam2d_tiny")
    >>> model = occam2d_to_pcsf(run)
    >>> model.kind, model.resistivity.shape
    ('grid2d', (4, 8))
    >>> model.stations.name
    ['S01', 'S02', 'S03']
    """
    wd = Path(workdir)
    if not wd.is_dir():
        raise AdapterError(f"{wd}: not a folder")
    iter_path = _pick_iteration(wd, iteration)
    it = native.read_iteration(iter_path)
    model_file = native.read_model(_named(wd, it.model_file, "model"))
    mesh = native.read_mesh(_named(wd, model_file.mesh_file, "mesh"))
    data = native.read_data(_named(wd, it.data_file, "data"))
    log_path = _find_log(wd)
    log = None if log_path is None else native.read_log(log_path)

    log10_rho = native.resistivity_grid(it.values, model_file, mesh)
    shift = chainage_shift(mesh.x_nodes, data.offsets)
    raw_nodes = mesh.x_nodes
    # Centres are shifted after averaging, as in pyCSAMT, so that
    # both implementations give bit-identical coordinates.
    x_centres = (raw_nodes[:-1] + raw_nodes[1:]) / 2.0 + shift
    x_nodes = raw_nodes + shift
    z_nodes = mesh.z_nodes
    geometry = Grid2DGeometry(
        x=x_centres,
        z=(z_nodes[:-1] + z_nodes[1:]) / 2.0,
        x_nodes=x_nodes,
        z_nodes=z_nodes,
        origin=None if origin is None else np.asarray(origin, float),
        azimuth_deg=azimuth_deg,
    )
    n = len(data.sites)
    stations, topography = station_table(
        data.sites,
        data.offsets,
        np.zeros(n),
        np.full(n, np.nan),
        station_lonlat=station_lonlat,
        station_elevations=station_elevations,
    )
    history: dict[str, np.ndarray] = {}
    metadata: dict[str, Any] = {
        "workdir": str(wd),
        "iteration_file": iter_path.name,
        "final_rms": it.misfit,
        "n_iterations": len(list(wd.glob("*.iter"))),
    }
    if log is not None:
        history = {
            "iteration": log.iteration.astype(float),
            "rms": log.rms,
            "roughness": log.roughness,
            "lagrange": log.lagrange,
            "stepsize": log.stepsize,
        }
        metadata["converged"] = log.converged
    return PCSFModel(
        geometry=geometry,
        resistivity=10.0**log10_rho,
        resistivity_native=log10_rho,
        resistivity_native_encoding="log10",
        stations=stations if n else None,
        topography=topography,
        survey=survey_dict(survey),
        history=history,
        source_backend="occam2d",
        created_by=created_by,
        crs=crs,
        description=description,
        metadata=metadata,
    )
