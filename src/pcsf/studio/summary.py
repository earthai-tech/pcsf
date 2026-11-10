"""Tables shown by the PCSF Studio inspector, and CSV exports.

Each function returns plain Python rows (strings and numbers), so
the inspector panes are thin Qt views over them and the same content
can be printed or tested without a display.
"""

from __future__ import annotations

import csv
from os import PathLike
from pathlib import Path
from typing import Any

import numpy as np

from ..api import info
from ..core.conformance import check_conformance
from ..core.record import check_inversion_record, get_inversion_record
from ..core.schema import PCSFModel
from .figures import AIR_THRESHOLD_OHM_M, _model_values

__all__ = [
    "cell_table",
    "conformance_rows",
    "metadata_tree",
    "record_rows",
    "station_rows",
    "summary_rows",
    "value_stats",
    "write_csv",
]

Row = tuple[str, str]


def _fmt(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (tuple, list)):
        return ", ".join(_fmt(v) for v in value)
    return str(value)


def _bounds(values: Any) -> str:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return "-"
    return f"{np.nanmin(arr):.6g} to {np.nanmax(arr):.6g} m"


def summary_rows(model: PCSFModel, source: str = "") -> list[Row]:
    """Key facts about a model, as ``(field, value)`` rows.

    Parameters
    ----------
    model : PCSFModel
        Model to describe.
    source : str, optional
        Where the model was read from, shown first when given.

    Returns
    -------
    list of tuple of str
        Geometry kind, shape, extent of each axis, resistivity range,
        encodings, CRS, solver, creator, creation time and
        description.

    Examples
    --------
    >>> from pcsf import datasets
    >>> from pcsf.studio.sources import open_source
    >>> from pcsf.studio.summary import summary_rows
    >>> rows = dict(summary_rows(open_source(
    ...     datasets.path("occam2d_tiny")).model))
    >>> rows["Geometry"], rows["Native encoding"]
    ('grid2d', 'log10')
    """
    d = info(model)
    g = model.geometry
    rows: list[Row] = []
    if source:
        rows.append(("Source", source))
    shape = d.get("shape")
    rows += [
        ("Geometry", model.kind),
        ("Shape", " x ".join(str(n) for n in shape) if shape else "-"),
        ("Cells", str(d["n_cells"])),
    ]
    if model.kind in ("grid2d", "grid3d"):
        for axis in ("x", "y", "z"):
            if hasattr(g, axis):
                rows.append(
                    (
                        f"{axis} extent",
                        _bounds(
                            getattr(g, f"{axis}_nodes")
                            if getattr(g, f"{axis}_nodes", None)
                            is not None
                            else getattr(g, axis)
                        ),
                    )
                )
        origin = getattr(g, "origin", None)
        if origin is not None:
            rows.append(
                ("Origin", _fmt([float(v) for v in np.ravel(origin)]))
            )
    elif model.kind == "mesh_unstructured":
        nodes = np.asarray(g.nodes, dtype=float)
        rows += [
            ("Plane", g.plane),
            ("Nodes", str(len(nodes))),
            (f"{g.plane[0]} extent", _bounds(nodes[:, 0])),
            (f"{g.plane[1]} extent", _bounds(nodes[:, 1])),
        ]
    elif model.kind == "multiline":
        rows.append(
            ("Lines", ", ".join(str(e.line_id) for e in g.lines))
        )
    rho = _model_values(model)
    rho = rho[np.isfinite(rho)]
    rows += [
        (
            "Resistivity",
            f"{rho.min():.4g} to {rho.max():.4g} ohm m"
            if rho.size
            else "-",
        ),
        ("Native encoding", _fmt(d["native_encoding"])),
        ("Stations", str(d["n_stations"])),
        ("CRS", _fmt(model.crs)),
        ("Solver", _fmt(model.source_backend)),
        ("Created by", _fmt(model.created_by)),
        ("Created at", _fmt(model.created_at)),
        ("Description", _fmt(model.description)),
    ]
    return rows


def station_rows(
    model: PCSFModel,
) -> tuple[list[str], list[list[Any]]]:
    """Station table as a header and rows.

    Parameters
    ----------
    model : PCSFModel
        Model whose station table is listed.

    Returns
    -------
    header : list of str
        Column names: ``name`` then the coordinate columns the table
        has (``x``, ``y``, ``z``, ``line_id``, ``lon``, ``lat``).
    rows : list of list
        One row per station; empty when there is no station table.
    """
    st = model.stations
    if st is None or len(st.name) == 0:
        return ["name"], []
    cols = [
        c
        for c in ("x", "y", "z", "line_id", "lon", "lat")
        if getattr(st, c) is not None
    ]
    rows = []
    for i, name in enumerate(st.name):
        row: list[Any] = [name]
        for c in cols:
            v = np.asarray(getattr(st, c))[i]
            row.append(v.item() if hasattr(v, "item") else v)
        rows.append(row)
    return ["name", *cols], rows


def _tree(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _tree(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)) and len(value) > 20:
        return f"list of {len(value)} items"
    if isinstance(value, (list, tuple)):
        return {str(i): _tree(v) for i, v in enumerate(value)}
    if isinstance(value, np.ndarray):
        return f"array {value.shape} {value.dtype}"
    if hasattr(value, "to_dict"):
        return _tree(value.to_dict())
    return value


def metadata_tree(model: PCSFModel) -> dict[str, Any]:
    """Survey, metadata, history and boreholes as a nested dict.

    Arrays are replaced by a ``"array (shape) dtype"`` string and
    long lists by their length, so the tree stays readable.

    Parameters
    ----------
    model : PCSFModel
        Model to describe.

    Returns
    -------
    dict
        Keys ``survey``, ``metadata``, ``history`` and
        ``boreholes``, for those the model has.
    """
    out: dict[str, Any] = {}
    for key in ("survey", "metadata", "history", "boreholes"):
        value = getattr(model, key)
        if value:
            out[key] = _tree(value)
    return out


def record_rows(
    model: PCSFModel,
) -> tuple[list[Row], list[str], list[str]]:
    """Inversion record fields and the fields it still lacks.

    Parameters
    ----------
    model : PCSFModel
        Model whose record (``metadata["inversion"]``) is listed.

    Returns
    -------
    rows : list of tuple of str
        ``(dotted field, value)`` for every field present; empty
        when the model has no record.
    missing_required, missing_recommended : list of str
        Dotted names reported by
        :func:`~pcsf.check_inversion_record`; all required fields
        are missing when there is no record.
    """
    from ..core.record import REQUIRED_FIELDS

    rec = get_inversion_record(model)
    if rec is None:
        return [], list(REQUIRED_FIELDS), []
    rows: list[Row] = []

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                walk(f"{prefix}.{k}" if prefix else str(k), v)
        elif value not in (None, "", [], {}):
            rows.append((prefix, _fmt(value)))

    walk("", rec.as_dict())
    miss = check_inversion_record(rec)
    return rows, list(miss["required"]), list(miss["recommended"])


def conformance_rows(model: PCSFModel) -> list[tuple[str, bool, str]]:
    """Result of every conformance rule.

    Parameters
    ----------
    model : PCSFModel
        Model to check.

    Returns
    -------
    list of tuple
        ``(rule, passed, message)`` per rule, in the order of
        :func:`~pcsf.check_conformance`.
    """
    report = check_conformance(model)
    return [
        (r.rule, bool(r.passed), r.message) for r in report.results
    ]


def value_stats(values: Any) -> dict[str, Any]:
    """Statistics of a set of resistivity values.

    Air cells (at or above :data:`~pcsf.studio.figures.
    AIR_THRESHOLD_OHM_M`) and missing values are counted, then left
    out of the statistics of the earth.

    Parameters
    ----------
    values : array_like
        Linear resistivity in ohm m, any shape.

    Returns
    -------
    dict
        ``n`` (values), ``n_missing`` (NaN or not positive),
        ``n_air``, ``n_earth``, and over the earth cells:
        ``min``, ``p05``, ``median``, ``p95``, ``max`` (ohm m) and
        ``log10_mean``, ``log10_std`` (decades). The earth
        statistics are None when there is no earth cell.

    Notes
    -----
    With :math:`r_i = \\log_{10}\\rho_i` over the :math:`n` earth
    cells, ``log10_mean`` is :math:`\\bar r = n^{-1}\\sum_i r_i` and
    ``log10_std`` the population standard deviation
    :math:`\\sqrt{n^{-1}\\sum_i (r_i - \\bar r)^2}`. Percentiles use
    linear interpolation (:func:`numpy.percentile`).

    Examples
    --------
    >>> from pcsf.studio.summary import value_stats
    >>> s = value_stats([10.0, 100.0, 1000.0, float("nan"), 1e12])
    >>> s["n_earth"], s["n_air"], s["n_missing"], s["median"]
    (3, 1, 1, 100.0)
    >>> round(s["log10_mean"], 6), round(s["log10_std"], 6)
    (2.0, 0.816497)
    """
    rho = np.ravel(np.asarray(values, dtype=float))
    ok = np.isfinite(rho) & (rho > 0)
    air = ok & (rho >= AIR_THRESHOLD_OHM_M)
    earth = rho[ok & ~air]
    out: dict[str, Any] = {
        "n": int(rho.size),
        "n_missing": int(rho.size - ok.sum()),
        "n_air": int(air.sum()),
        "n_earth": int(earth.size),
    }
    keys = (
        "min",
        "p05",
        "median",
        "p95",
        "max",
        "log10_mean",
        "log10_std",
    )
    if earth.size == 0:
        return {**out, **dict.fromkeys(keys)}
    p = np.percentile(earth, [0, 5, 50, 95, 100])
    r = np.log10(earth)
    return {
        **out,
        **{k: float(v) for k, v in zip(keys[:5], p)},
        "log10_mean": float(r.mean()),
        "log10_std": float(r.std()),
    }


def cell_table(model: PCSFModel) -> tuple[list[str], np.ndarray]:
    """Cell centres and resistivity as a table.

    Parameters
    ----------
    model : PCSFModel
        Model to tabulate.

    Returns
    -------
    header : list of str
        Column names, ending with ``rho_ohm_m``: ``x, z`` for
        ``grid2d``; ``x, y, z`` for ``grid3d``; the two plane axes
        (triangle centroids) for meshes; ``line, x, z`` for
        ``multiline``.
    table : ndarray of float, shape (n_cells, n_columns)
        One row per cell, in the C order of the resistivity array.
    """
    g = model.geometry
    rho = (
        np.asarray(model.resistivity, dtype=float)
        if (model.kind != "multiline")
        else None
    )
    if model.kind == "grid2d":
        zz, xx = np.meshgrid(g.z, g.x, indexing="ij")
        return ["x", "z", "rho_ohm_m"], np.column_stack(
            [xx.ravel(), zz.ravel(), rho.ravel()]
        )
    if model.kind == "grid3d":
        zz, yy, xx = np.meshgrid(g.z, g.y, g.x, indexing="ij")
        return ["x", "y", "z", "rho_ohm_m"], np.column_stack(
            [xx.ravel(), yy.ravel(), zz.ravel(), rho.ravel()]
        )
    if model.kind == "mesh_unstructured":
        nodes = np.asarray(g.nodes, dtype=float)
        cen = nodes[np.asarray(g.connectivity)].mean(axis=1)
        return [g.plane[0], g.plane[1], "rho_ohm_m"], np.column_stack(
            [cen, rho.ravel()]
        )
    blocks = []
    for k, e in enumerate(g.lines):
        zz, xx = np.meshgrid(e.geometry.z, e.geometry.x, indexing="ij")
        r = np.asarray(e.resistivity, dtype=float).ravel()
        blocks.append(
            np.column_stack(
                [np.full(r.size, k), xx.ravel(), zz.ravel(), r]
            )
        )
    table = np.vstack(blocks) if blocks else np.empty((0, 4))
    return ["line", "x", "z", "rho_ohm_m"], table


def write_csv(
    path: str | PathLike[str], header: list[str], rows: Any
) -> Path:
    """Write a header and rows to a CSV file.

    Parameters
    ----------
    path : path-like
        Destination file, overwritten.
    header : list of str
        Column names.
    rows : iterable of sequences or 2-D ndarray
        Table body.

    Returns
    -------
    Path
        *path*.

    Examples
    --------
    >>> import tempfile, pathlib
    >>> from pcsf import datasets
    >>> from pcsf.studio.sources import open_source
    >>> from pcsf.studio.summary import cell_table, write_csv
    >>> m = open_source(datasets.path("occam2d_tiny")).model
    >>> header, table = cell_table(m)
    >>> with tempfile.TemporaryDirectory() as d:
    ...     p = write_csv(pathlib.Path(d) / "cells.csv", header, table)
    ...     p.read_text().splitlines()[0]
    'x,z,rho_ohm_m'
    """
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for row in rows:
            w.writerow(
                [
                    repr(float(v))
                    if isinstance(v, (float, np.floating))
                    else v
                    for v in row
                ]
            )
    return path
