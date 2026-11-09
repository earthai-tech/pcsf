"""EarthScope Earth Model Collaboration (EMC) netCDF files.

EMC [1]_ archives 3-D models as netCDF files on a geographic grid
(longitude, latitude, depth in km). :func:`emc_to_pcsf` converts
such a file to a ``grid3d`` model and :func:`pcsf_to_emc` writes it
back; the pair is lossless: values (fill values included), coordinate
and value types, every global and variable attribute with its type,
and the netCDF format are restored. Needs ``pcsf[emc]`` (netCDF4).

Notes
-----
Electrical models in EMC usually store
:math:`\\log_{10}\\sigma` with :math:`\\sigma` in S/m, which pcsf
records with encoding ``log10_conductivity``, so that
:math:`\\rho = 10^{-v}`. Depth is converted from km to m, and the
grid's horizontal coordinates stay in degrees with
``crs = "EPSG:4326"``.

References
----------
.. [1] Trabant, C., A. R. Hutko, M. Bahavar, R. Karstens, T. Ahern,
   and R. Aster, 2012, Data products at the IRIS DMC: Stepping
   stones for research and other applications: Seismological
   Research Letters, 83, 846-854.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from ..api.registry import register_adapter
from ..compat.optional import import_optional
from ..core.schema import Grid3DGeometry, PCSFModel
from ..exceptions import AdapterError

__all__ = ["emc_to_pcsf", "pcsf_to_emc"]

_COORDS = ("depth", "latitude", "longitude")
_ENCODINGS = {
    "log10_conductivity": "log10_conductivity",
    "log10_resistivity": "log10",
    "conductivity": "conductivity",
    "resistivity": "linear",
}


def _pack(value: Any) -> dict[str, Any]:
    """Attribute value with its type, as JSON-ready data."""
    if isinstance(value, str):
        return {"t": "str", "v": value}
    arr = np.asarray(value)
    return {"t": arr.dtype.str, "v": arr.tolist()}


def _unpack(packed: dict[str, Any]) -> Any:
    if packed["t"] == "str":
        return packed["v"]
    return np.array(packed["v"], dtype=np.dtype(packed["t"]))


def _encoding(name: str, attrs: dict[str, Any]) -> str:
    """Resistivity encoding of an EMC variable from its name."""
    text = " ".join(
        [
            name,
            str(attrs.get("long_name", "")),
            str(attrs.get("units", "")),
        ]
    ).lower()
    for key in ("log10_conductivity", "log10_resistivity"):
        if key in text.replace(" ", "_") or key in name.lower():
            return _ENCODINGS[key]
    if "log" in text and "conduct" in text:
        return "log10_conductivity"
    if "log" in text:
        return "log10"
    if "conduct" in text:
        return "conductivity"
    return "linear"


@register_adapter("emc")
def emc_to_pcsf(
    path: str | os.PathLike[str],
    *,
    variable: str | None = None,
    encoding: str | None = None,
    created_by: str = "",
    description: str = "",
) -> PCSFModel:
    """Convert an EMC netCDF model to a ``grid3d`` model.

    Parameters
    ----------
    path : str or os.PathLike
        netCDF file.
    variable : str, optional
        3-D variable to convert; the first 3-D variable by default.
    encoding : str, optional
        Encoding of the values; guessed from the variable's name,
        ``long_name`` and ``units`` by default (usually
        ``log10_conductivity``).
    created_by, description : str, optional
        Stored in the model; the description defaults to the file's
        ``id`` and ``title``.

    Returns
    -------
    PCSFModel
        ``grid3d`` model with axes ``(depth, latitude, longitude)``,
        depth in metres, linear resistivity, the archived values as
        source values (fill values as NaN), ``crs = "EPSG:4326"``,
        and ``metadata["emc"]`` holding everything
        :func:`pcsf_to_emc` needs.

    Raises
    ------
    MissingDependencyError
        If netCDF4 is not installed.
    AdapterError
        If the file has no 3-D variable or lacks a coordinate.

    See Also
    --------
    pcsf_to_emc : Inverse conversion.

    Examples
    --------
    >>> from pcsf.adapters.emc import emc_to_pcsf
    >>> model = emc_to_pcsf("WUS.MT.nc")  # doctest: +SKIP
    >>> model.resistivity_native_encoding  # doctest: +SKIP
    'log10_conductivity'
    """
    nc = import_optional("netCDF4", feature="EMC netCDF files")
    with nc.Dataset(path) as d:
        d.set_auto_mask(False)
        names = [v for v in d.variables if d[v].ndim == 3]
        var = variable or (names[0] if names else None)
        if var is None or var not in d.variables:
            raise AdapterError(f"{path}: no 3-D variable to convert")
        dims = list(d[var].dimensions)
        if sorted(dims) != sorted(_COORDS):
            raise AdapterError(
                f"{path}: {var} has dimensions {dims}, expected "
                f"{list(_COORDS)}"
            )
        v = d[var]
        raw = v[:]
        attrs = {a: v.getncattr(a) for a in v.ncattrs()}
        fill = attrs.get("_FillValue")
        native = raw.astype(np.float64)
        if fill is not None:
            native[raw == fill] = np.nan
        order = [dims.index(c) for c in _COORDS]
        native = np.transpose(native, order)
        coords = {c: np.asarray(d[c][:]) for c in _COORDS}
        meta = {
            "file_format": d.data_model,
            "variable": var,
            "dimensions": dims,
            "coordinate_dtypes": {
                c: coords[c].dtype.str for c in _COORDS
            },
            "value_dtype": v.dtype.str,
            "depth_units": getattr(d["depth"], "units", "km"),
            "global_attributes": {
                a: _pack(d.getncattr(a)) for a in d.ncattrs()
            },
            "variable_attributes": {
                n: {
                    a: _pack(d[n].getncattr(a)) for a in d[n].ncattrs()
                }
                for n in d.variables
            },
        }
        gattrs = {a: d.getncattr(a) for a in d.ncattrs()}
    enc = encoding or _encoding(var, attrs)
    from ..core.encodings import to_resistivity

    scale = 1000.0 if str(meta["depth_units"]).lower() == "km" else 1.0
    geometry = Grid3DGeometry(
        x=coords["longitude"].astype(np.float64),
        y=coords["latitude"].astype(np.float64),
        z=coords["depth"].astype(np.float64) * scale,
    )
    if not description:
        description = (
            f"EMC model {gattrs.get('id', Path(path).stem)}: "
            f"{gattrs.get('title', '')}"
        )
    return PCSFModel(
        geometry=geometry,
        resistivity=to_resistivity(native, enc),
        resistivity_native=native,
        resistivity_native_encoding=enc,
        source_backend="emc",
        created_by=created_by,
        crs="EPSG:4326",
        description=description,
        metadata={"emc": meta},
    )


def pcsf_to_emc(
    model: PCSFModel, path: str | os.PathLike[str]
) -> Path:
    """Write a model converted by :func:`emc_to_pcsf` back to EMC.

    Parameters
    ----------
    model : PCSFModel
        Model carrying ``metadata["emc"]``, possibly after a round
        trip through PCSF or PCSM files.
    path : str or os.PathLike
        Destination netCDF file.

    Returns
    -------
    pathlib.Path
        *path*.

    Raises
    ------
    MissingDependencyError
        If netCDF4 is not installed.
    AdapterError
        If the model has no EMC metadata or source values.

    See Also
    --------
    emc_to_pcsf : Forward conversion.

    Notes
    -----
    Values are taken from the source values, not recomputed from the
    canonical resistivity, so that the archived numbers are restored
    bit for bit; NaN becomes the fill value again.

    Examples
    --------
    >>> from pcsf.adapters.emc import emc_to_pcsf, pcsf_to_emc
    >>> model = emc_to_pcsf("WUS.MT.nc")  # doctest: +SKIP
    >>> pcsf_to_emc(model, "copy.nc")  # doctest: +SKIP
    """
    nc = import_optional("netCDF4", feature="EMC netCDF files")
    meta = (model.metadata or {}).get("emc")
    if meta is None or model.resistivity_native is None:
        raise AdapterError(
            "model has no EMC metadata or source values; it was not "
            "made by emc_to_pcsf"
        )
    path = Path(path)
    var = meta["variable"]
    vattrs = meta["variable_attributes"]
    dims = list(meta["dimensions"])
    geo = model.geometry
    scale = 1000.0 if str(meta["depth_units"]).lower() == "km" else 1.0
    coords = {
        "longitude": geo.x,
        "latitude": geo.y,
        "depth": geo.z / scale,
    }
    data = np.asarray(model.resistivity_native, dtype=np.float64)
    data = np.transpose(data, [_COORDS.index(c) for c in dims])
    with nc.Dataset(path, "w", format=meta["file_format"]) as d:
        for c in dims:
            d.createDimension(c, coords[c].size)
        for c in ("longitude", "latitude", "depth"):
            dt = np.dtype(meta["coordinate_dtypes"][c])
            v = d.createVariable(c, dt, (c,))
            for a, p in vattrs.get(c, {}).items():
                v.setncattr(a, _unpack(p))
            v[:] = coords[c].astype(dt)
        fill = None
        if "_FillValue" in vattrs[var]:
            fill = _unpack(vattrs[var]["_FillValue"])
        v = d.createVariable(
            var,
            np.dtype(meta["value_dtype"]),
            tuple(dims),
            fill_value=fill,
        )
        v.set_auto_mask(False)
        for a, p in vattrs[var].items():
            if a != "_FillValue":
                v.setncattr(a, _unpack(p))
        if fill is not None:
            data = np.where(np.isnan(data), float(fill), data)
        v[:] = data.astype(np.dtype(meta["value_dtype"]))
        for a, p in meta["global_attributes"].items():
            d.setncattr(a, _unpack(p))
    return path
