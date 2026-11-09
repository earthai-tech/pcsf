"""ModEM files to a ``grid3d`` PCSF model.

See Also
--------
pcsf.native.modem : Parsers of the individual files.
"""

from __future__ import annotations

import os
import re
import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from ..api.registry import register_adapter
from ..core.schema import Grid3DGeometry, PCSFModel
from ..native import modem as native
from ._common import station_table, survey_dict

__all__ = [
    "DEFAULT_AIR_THRESHOLD_OHM_M",
    "mask_air",
    "modem_to_pcsf",
    "station_elevation",
]

#: Resistivity (ohm m) above which a cell is taken as air fill.
#: Rocks rarely exceed a few times 1e4 ohm m, while ModEM air fill
#: is 1e8 to 1e13 ohm m.
DEFAULT_AIR_THRESHOLD_OHM_M = 1e8

_DEPTH_MARKERS = (
    "depth below",
    "positive down",
    "positive-down",
    "z(m) is depth",
    "z is depth",
    "z down",
    "z-down",
)
_DATUM = re.compile(r"(-?\d+(?:\.\d+)?)\s*m\s*a\.?\s*s\.?\s*l")


def mask_air(
    rho: np.ndarray, threshold: float
) -> tuple[np.ndarray, int]:
    """Replace air-fill cells by NaN.

    Parameters
    ----------
    rho : array_like of shape (n_z, n_y, n_x)
        Linear resistivity, ohm m.
    threshold : float
        Cells above it are air.

    Returns
    -------
    masked : ndarray
        Copy of *rho* with air cells set to NaN.
    n_air : int
        Leading layers made entirely of air.

    Notes
    -----
    Uneven topography seldom leaves a layer entirely in the air, so
    *n_air* is often zero while many cells are masked; the per-cell
    mask is what matters for display and comparison.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.adapters.modem import mask_air
    >>> rho = np.array([[[1e12, 1e12]], [[1e12, 50.0]]])
    >>> masked, n_air = mask_air(rho, 1e8)
    >>> n_air, int(np.isnan(masked).sum())
    (1, 3)
    """
    r = np.asarray(rho, dtype=float)
    air = r > threshold
    masked = np.where(air, np.nan, r)
    n_air = 0
    if r.ndim == 3:
        for is_air in air.all(axis=(1, 2)):
            if not is_air:
                break
            n_air += 1
    return masked, n_air


def station_elevation(
    z: np.ndarray, comment: str, convention: str = "auto"
) -> tuple[np.ndarray, dict[str, Any]]:
    """Station ``Z`` of a ModEM data file as a positive-up elevation.

    Parameters
    ----------
    z : array_like
        ``Z`` column of the data file, metres.
    comment : str
        Comment lines of the data file.
    convention : {"auto", "elevation", "depth_down"}, default "auto"
        ``"elevation"`` keeps *z*; ``"depth_down"`` converts it;
        ``"auto"`` converts only when the comment says the column is
        a depth.

    Returns
    -------
    elevation : ndarray
        Elevation, metres.
    info : dict
        ``convention``, ``flipped`` and, when flipped,
        ``datum_masl`` (None when the comment gives no datum).

    Raises
    ------
    ValueError
        If *convention* is unknown.

    Notes
    -----
    ModEM's :math:`z` axis points down, so a populated ``Z`` column
    is a depth :math:`d` below a datum, but some writers store an
    elevation there. A depth is converted as :math:`h = h_0 - d`,
    with :math:`h_0` read from a comment such as ``224 m a.s.l.``;
    without one, :math:`h = \\max d - d` keeps the relief without an
    absolute level. An all-zero column (no topography) is kept.

    Examples
    --------
    >>> from pcsf.adapters.modem import station_elevation
    >>> h, info = station_elevation([0.0, 30.0],
    ...                             "Z is depth below 224 m a.s.l.")
    >>> h.tolist(), info["datum_masl"]
    ([224.0, 194.0], 224.0)
    """
    if convention not in ("auto", "elevation", "depth_down"):
        raise ValueError(f"unknown convention {convention!r}")
    z = np.asarray(z, dtype=float)
    info: dict[str, Any] = {"convention": convention, "flipped": False}
    has_values = np.any(np.isfinite(z) & (z != 0.0))
    if not has_values or convention == "elevation":
        return z, info
    text = (comment or "").lower()
    is_depth = convention == "depth_down" or any(
        marker in text for marker in _DEPTH_MARKERS
    )
    if not is_depth:
        return z, info
    match = _DATUM.search(text)
    datum = float(match.group(1)) if match else None
    elevation = (datum if datum is not None else np.nanmax(z)) - z
    info.update(flipped=True, datum_masl=datum)
    return elevation, info


def _warn_quantised(lonlat: np.ndarray) -> None:
    vals = lonlat[np.isfinite(lonlat)]
    if vals.size >= 6 and np.all(
        np.abs(vals - np.round(vals, 3)) < 1e-9
    ):
        warnings.warn(
            "station longitude and latitude are rounded to 3 decimals "
            "(about 100 m), as in a ModEM rewrite of the data file; "
            "nearby stations may collapse onto one point",
            UserWarning,
            stacklevel=3,
        )


@register_adapter("modem")
def modem_to_pcsf(
    model: str | os.PathLike[str],
    *,
    data: str | os.PathLike[str] | None = None,
    log: str | os.PathLike[str] | None = None,
    air_threshold_ohm_m: float | None = DEFAULT_AIR_THRESHOLD_OHM_M,
    station_z_convention: str = "auto",
    station_elevations: Mapping[str, float] | None = None,
    survey: Any = None,
    created_by: str = "",
    crs: str | None = None,
    description: str = "",
) -> PCSFModel:
    """Convert ModEM 3-D files to a ``grid3d`` model.

    Parameters
    ----------
    model : str or os.PathLike
        ``.rho`` model file, usually the last ``*_NLCG_NNN.rho``.
    data : str or os.PathLike, optional
        ``.dat`` data file, for the station table.
    log : str or os.PathLike, optional
        NLCG log file, for the iteration history.
    air_threshold_ohm_m : float or None, default 1e8
        Cells above it become NaN (air fill); ``None`` keeps every
        value.
    station_z_convention : {"auto", "elevation", "depth_down"}
        Meaning of the data file's ``Z`` column; see
        :func:`station_elevation`.
    station_elevations : mapping of str to float, optional
        Elevations replacing ``Z`` for the stations they name; they
        define the topography.
    survey : mapping or object, optional
        Survey metadata.
    created_by, crs, description : str, optional
        Stored in the model.

    Returns
    -------
    PCSFModel
        Linear resistivity with the file's :math:`\\ln\\rho` kept as
        source values (encoding ``ln``, air cells included), grid
        origin and rotation, stations and history when given, and
        metadata ``model_file``, ``final_rms``, ``n_iter``,
        ``air_mask`` and ``station_z`` where they apply.

    Raises
    ------
    FormatError
        If a file is malformed.

    Warns
    -----
    UserWarning
        When the ``Z`` column is converted from a depth, or station
        positions are rounded to 3 decimals.

    See Also
    --------
    mask_air, station_elevation
    pcsf.native.modem : File parsers.

    Notes
    -----
    Cell centres are midpoints of the cell edges, which start at
    zero; the grid origin is stored separately, so model-frame
    coordinates are not shifted.

    Examples
    --------
    >>> import pcsf
    >>> from pcsf.adapters import modem_to_pcsf
    >>> run = pcsf.datasets.path("modem_tiny")
    >>> model = modem_to_pcsf(run / "tiny_NLCG_002.rho",
    ...                       data=run / "tiny.dat",
    ...                       log=run / "tiny_NLCG.log",
    ...                       station_z_convention="elevation")
    >>> model.kind, model.resistivity.shape, len(model.stations.name)
    ('grid3d', (3, 4, 5), 2)
    """
    mod = native.read_model(model)
    xn, yn, zn = mod.x_nodes, mod.y_nodes, mod.z_nodes
    rho = np.exp(mod.log_rho)
    n_air = int(mod.n_air)
    metadata: dict[str, Any] = {"model_file": Path(model).name}
    if air_threshold_ohm_m is not None:
        masked, detected = mask_air(rho, float(air_threshold_ohm_m))
        n_masked = int(
            np.count_nonzero(np.isnan(masked) & ~np.isnan(rho))
        )
        if n_masked:
            rho = masked
            if n_air == 0 and detected > 0:
                n_air = detected
            metadata["air_mask"] = {
                "threshold_ohm_m": float(air_threshold_ohm_m),
                "n_cells_masked": n_masked,
                "n_air_detected": detected,
            }
    geometry = Grid3DGeometry(
        x=(xn[:-1] + xn[1:]) / 2.0,
        y=(yn[:-1] + yn[1:]) / 2.0,
        z=(zn[:-1] + zn[1:]) / 2.0,
        x_nodes=xn,
        y_nodes=yn,
        z_nodes=zn,
        origin=np.asarray(mod.origin, dtype=float),
        rotation_deg=float(mod.rotation),
        n_air=n_air,
    )
    stations = topography = None
    if data is not None:
        dat = native.read_data(data)
        z, info = station_elevation(
            dat.xyz[:, 2], dat.comment, station_z_convention
        )
        metadata["station_z"] = info
        if info["flipped"]:
            warnings.warn(
                "the ModEM Z column reads as a depth; converted to "
                f"elevation (datum {info['datum_masl']} m a.s.l.); "
                "pass station_z_convention='elevation' to keep it",
                UserWarning,
                stacklevel=2,
            )
        ll = dat.lonlat
        if np.isfinite(ll).any():
            _warn_quantised(ll[np.isfinite(ll).all(axis=1)])
        lonlat = {
            s: (float(lo), float(la))
            for s, (lo, la) in zip(dat.sites, ll)
        }
        stations, topography = station_table(
            dat.sites,
            dat.xyz[:, 0],
            dat.xyz[:, 1],
            z,
            station_lonlat=lonlat,
            station_elevations=station_elevations,
        )
    history: dict[str, np.ndarray] = {}
    if log is not None:
        lg = native.read_log(log)
        history = {
            "iteration": lg.iteration.astype(float),
            "rms": lg.rms,
            "objective": lg.objective,
            "model_norm": lg.model_norm,
            "lagrange": lg.lagrange,
            "alpha": lg.alpha,
        }
        metadata["final_rms"] = (
            float(lg.rms[-1]) if lg.rms.size else float("nan")
        )
        metadata["n_iter"] = int(lg.iteration.size)
    return PCSFModel(
        geometry=geometry,
        resistivity=rho,
        resistivity_native=mod.log_rho,
        resistivity_native_encoding="ln",
        stations=stations,
        topography=topography,
        survey=survey_dict(survey),
        history=history,
        source_backend="modem3d",
        created_by=created_by,
        crs=crs,
        description=description,
        metadata=metadata,
    )
