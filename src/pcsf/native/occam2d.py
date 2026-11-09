"""Parsers of Occam2D files.

Occam2D [1]_ describes a 2-D magnetotelluric inversion with four
text files: a finite-element mesh (PW2D), a model file grouping mesh
cells into parameter blocks, a data file with the station names and
offsets, and one iteration file per iteration holding the
parameter values in log10 ohm m. A log file records the misfit,
roughness, Lagrange multiplier and step size of each iteration.

The functions here read those files with NumPy only and
:func:`resistivity_grid` assembles the per-cell log10 resistivity.

Notes
-----
The mesh has :math:`N_x` columns of widths :math:`\\Delta x_i` and
:math:`N_z` rows of thicknesses :math:`\\Delta z_k`; node coordinates
are cumulative sums starting at zero. Model layer :math:`\\ell`
covers :math:`n_\\ell` consecutive mesh rows below the air rows and
is split into blocks of :math:`c_{\\ell j}` consecutive mesh columns;
block parameters are numbered row by row, so the :math:`p`-th value
of the iteration file fills the :math:`p`-th block.

References
----------
.. [1] deGroot-Hedlin, C., and S. Constable, 1990, Occam's inversion
   to generate smooth, two-dimensional models from magnetotelluric
   data: Geophysics, 55, 1613-1624.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np

from ..exceptions import FormatError
from ._tokens import header_value, read_lines

__all__ = [
    "OccamData",
    "OccamIteration",
    "OccamLog",
    "OccamMesh",
    "OccamModel",
    "read_data",
    "read_iteration",
    "read_log",
    "read_mesh",
    "read_model",
    "resistivity_grid",
]

_MODEL_TAG = "OCCAM2MTMOD_1.0"
_ITER_TAG = "OCCAMITER_FLEX"
_DATA_TAG = "OCCAM2MTDATA_1.0"


@dataclass
class OccamMesh:
    """Occam2D PW2D mesh.

    Attributes
    ----------
    x_widths : ndarray of shape (n_x,)
        Column widths, metres.
    z_widths : ndarray of shape (n_z,)
        Row thicknesses, metres, air rows included.
    n_air : int
        Leading rows that are entirely air (cell code ``0``).
    comment : str
        First line of the file.
    """

    x_widths: np.ndarray
    z_widths: np.ndarray
    n_air: int = 0
    comment: str = ""

    @property
    def x_nodes(self) -> np.ndarray:
        """Column edges, metres, starting at zero."""
        return np.concatenate([[0.0], np.cumsum(self.x_widths)])

    @property
    def z_nodes(self) -> np.ndarray:
        """Row edges, metres, starting at zero."""
        return np.concatenate([[0.0], np.cumsum(self.z_widths)])


@dataclass
class OccamModel:
    """Occam2D model file: grouping of mesh cells into blocks.

    Attributes
    ----------
    layers : list of tuple
        ``(n_rows, column_counts)`` per model layer: the number of
        mesh rows merged and the mesh-column count of each block.
    mesh_file : str
        Mesh file name recorded in the header.
    header : dict
        Every ``Key: value`` header line, keys in upper case.
    """

    layers: list[tuple[int, np.ndarray]]
    mesh_file: str = ""
    header: dict[str, str] = field(default_factory=dict)

    @property
    def n_params(self) -> int:
        """Number of model parameters (blocks)."""
        return int(sum(len(cols) for _, cols in self.layers))


@dataclass
class OccamIteration:
    """One Occam2D iteration file.

    Attributes
    ----------
    values : ndarray of shape (n_params,)
        Parameter values, log10 ohm m.
    iteration : int
        Iteration number.
    misfit : float
        RMS misfit of this iteration.
    roughness, lagrange : float
        Model roughness and Lagrange multiplier.
    model_file, data_file : str
        File names recorded in the header.
    header : dict
        Every ``Key: value`` header line, keys in upper case.
    """

    values: np.ndarray
    iteration: int = -1
    misfit: float = float("nan")
    roughness: float = float("nan")
    lagrange: float = float("nan")
    model_file: str = ""
    data_file: str = ""
    header: dict[str, str] = field(default_factory=dict)


@dataclass
class OccamData:
    """Station part of an Occam2D data file.

    Attributes
    ----------
    sites : list of str
        Station names in file order.
    offsets : ndarray of shape (n_sites,)
        Station positions along the profile, metres.
    title : str
        Title line.
    """

    sites: list[str]
    offsets: np.ndarray
    title: str = ""


@dataclass
class OccamLog:
    """Iteration history from an Occam2D log file.

    Attributes
    ----------
    iteration : ndarray of int
        Iteration numbers.
    rms, roughness, lagrange, stepsize : ndarray of float
        Value of each quantity at the accepted step; NaN when the
        log does not report it.
    """

    iteration: np.ndarray
    rms: np.ndarray
    roughness: np.ndarray
    lagrange: np.ndarray
    stepsize: np.ndarray

    @property
    def converged(self) -> bool:
        """Whether any iteration reached an RMS of 1 or less."""
        finite = self.rms[np.isfinite(self.rms)]
        return bool(finite.size and finite.min() <= 1.0)


def _floats(tokens: list[str]) -> list[float]:
    out = []
    for tok in tokens:
        try:
            out.append(float(tok))
        except ValueError:
            continue
    return out


def read_mesh(path: str | os.PathLike[str]) -> OccamMesh:
    """Read an Occam2D PW2D mesh file.

    Parameters
    ----------
    path : str or os.PathLike
        Mesh file (usually ``Occam2DMesh``).

    Returns
    -------
    OccamMesh

    Raises
    ------
    FormatError
        If the file is missing, too short, or its control line or
        widths cannot be read.

    Notes
    -----
    The control line holds the node counts
    :math:`N_x + 1` and :math:`N_z + 1`. Widths follow, then a line
    ``0`` and four character rows per mesh row; a mesh row whose
    four rows contain only ``0`` is air. Leading air rows are
    counted.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.native.occam2d import read_mesh
    >>> text = "MESH\\n0 3 3 0 0 2\\n10 20\\n5 15\\n0\\n" + "??\\n" * 8
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = os.path.join(tmp, "mesh")
    ...     _ = open(p, "w").write(text)
    ...     mesh = read_mesh(p)
    >>> print(mesh.x_nodes, mesh.n_air)
    [ 0. 10. 30.] 0
    """
    lines = read_lines(path)
    if len(lines) < 2:
        raise FormatError(f"{path}: Occam2D mesh file too short")
    ctrl = lines[1].split()
    try:
        n_x = int(ctrl[1]) - 1
        n_z = int(ctrl[2]) - 1
    except (IndexError, ValueError) as exc:
        raise FormatError(
            f"{path}: cannot parse mesh control line {lines[1]!r}"
        ) from exc
    widths: list[float] = []
    rows: list[str] = []
    in_rows = False
    for raw in lines[2:]:
        text = raw.strip()
        if not text:
            continue
        if in_rows:
            rows.append(text)
        elif text == "0" and len(widths) >= n_x + n_z:
            in_rows = True
        else:
            widths.extend(_floats(text.split()))
    if len(widths) < n_x + n_z:
        raise FormatError(
            f"{path}: expected {n_x + n_z} widths, got {len(widths)}"
        )
    n_air = 0
    for start in range(0, len(rows) - 3, 4):
        if all(set(r) <= {"0"} for r in rows[start : start + 4]):
            n_air += 1
        else:
            break
    return OccamMesh(
        x_widths=np.array(widths[:n_x], dtype=float),
        z_widths=np.array(widths[n_x : n_x + n_z], dtype=float),
        n_air=n_air,
        comment=lines[0].strip(),
    )


def read_model(path: str | os.PathLike[str]) -> OccamModel:
    """Read an Occam2D model file (``OCCAM2MTMOD_1.0``).

    Parameters
    ----------
    path : str or os.PathLike
        Model file (usually ``Occam2DModel``).

    Returns
    -------
    OccamModel

    Raises
    ------
    FormatError
        If the format tag is wrong or a layer block is malformed.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.native.occam2d import read_model
    >>> text = ("Format: OCCAM2MTMOD_1.0\\nMesh File: mesh\\n"
    ...         "Num Layers: 1\\n1 2\\n1 1\\n")
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = os.path.join(tmp, "model")
    ...     _ = open(p, "w").write(text)
    ...     model = read_model(p)
    >>> model.mesh_file, model.n_params
    ('mesh', 2)
    """
    lines = read_lines(path)
    header: dict[str, str] = {}
    layers: list[tuple[int, np.ndarray]] = []
    i = 0
    while i < len(lines):
        kv = header_value(lines[i].strip())
        i += 1
        if kv is None:
            continue
        key, value = kv
        header[key] = value
        if key != "NUM LAYERS":
            continue
        try:
            for _ in range(int(float(value))):
                while not lines[i].strip():
                    i += 1
                n_rows = int(lines[i].split()[0])
                i += 1
                while not lines[i].strip():
                    i += 1
                cols = np.array(lines[i].split(), dtype=np.int64)
                i += 1
                layers.append((n_rows, cols))
        except (IndexError, ValueError) as exc:
            raise FormatError(
                f"{path}: malformed model layer block"
            ) from exc
        break
    tag = header.get("FORMAT", "")
    if tag.upper() != _MODEL_TAG:
        raise FormatError(
            f"{path}: expected format {_MODEL_TAG!r}, got {tag!r}"
        )
    return OccamModel(layers, header.get("MESH FILE", ""), header)


def _to_float(value: str | None) -> float:
    try:
        return float(value) if value is not None else float("nan")
    except ValueError:
        return float("nan")


def read_iteration(path: str | os.PathLike[str]) -> OccamIteration:
    """Read an Occam2D iteration file (``OCCAMITER_FLEX``).

    Parameters
    ----------
    path : str or os.PathLike
        Iteration file, such as ``ITER54.iter``; the startup file
        has the same format.

    Returns
    -------
    OccamIteration
        Header values and the parameter vector. A truncated vector
        is padded with NaN to the declared ``Param Count``.

    Raises
    ------
    FormatError
        If the format tag is missing or wrong.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.native.occam2d import read_iteration
    >>> text = ("Format: OCCAMITER_FLEX\\nIteration: 3\\n"
    ...         "Misfit Value: 1.2\\nParam Count: 2\\n2.0 2.5\\n")
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = os.path.join(tmp, "ITER03.iter")
    ...     _ = open(p, "w").write(text)
    ...     it = read_iteration(p)
    >>> it.iteration, it.misfit, it.values.tolist()
    (3, 1.2, [2.0, 2.5])
    """
    header: dict[str, str] = {}
    tokens: list[str] = []
    reading = False
    for raw in read_lines(path):
        text = raw.strip()
        if not text or text.startswith("!"):
            continue
        if reading:
            tokens.extend(text.split())
            continue
        kv = header_value(text)
        if kv is None:
            continue
        header[kv[0]] = kv[1]
        if kv[0] == "PARAM COUNT":
            reading = True
    tag = header.get("FORMAT", "")
    if tag.upper() != _ITER_TAG:
        raise FormatError(
            f"{path}: expected format {_ITER_TAG!r}, got {tag!r}"
        )
    n = int(_to_float(header.get("PARAM COUNT", "0")))
    values = np.array(_floats(tokens[:n]), dtype=float)
    if values.size < n:
        values = np.concatenate(
            [values, np.full(n - values.size, np.nan)]
        )
    it = _to_float(header.get("ITERATION"))
    return OccamIteration(
        values=values,
        iteration=int(it) if np.isfinite(it) else -1,
        misfit=_to_float(header.get("MISFIT VALUE")),
        roughness=_to_float(header.get("ROUGHNESS VALUE")),
        lagrange=_to_float(header.get("LAGRANGE VALUE")),
        model_file=header.get("MODEL FILE", ""),
        data_file=header.get("DATA FILE", ""),
        header=header,
    )


def read_data(path: str | os.PathLike[str]) -> OccamData:
    """Read station names and offsets of an Occam2D data file.

    Parameters
    ----------
    path : str or os.PathLike
        Data file (``OCCAM2MTDATA_1.0``).

    Returns
    -------
    OccamData
        Only the station block is read; frequencies and data rows
        are not needed to build a model.

    Raises
    ------
    FormatError
        If the format tag is wrong, or names and offsets differ in
        number.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.native.occam2d import read_data
    >>> text = ("FORMAT: OCCAM2MTDATA_1.0\\nTITLE: t\\nSITES: 2\\n"
    ...         "A\\nB\\nOFFSETS (M): 2\\n0.0\\n50.0\\n")
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = os.path.join(tmp, "data.dat")
    ...     _ = open(p, "w").write(text)
    ...     d = read_data(p)
    >>> d.sites, d.offsets.tolist()
    (['A', 'B'], [0.0, 50.0])
    """
    lines = read_lines(path)
    tag = title = ""
    sites: list[str] = []
    offsets: list[float] = []
    i = 0
    while i < len(lines):
        kv = header_value(lines[i].strip())
        i += 1
        if kv is None:
            continue
        key, value = kv
        if key == "FORMAT":
            tag = value
        elif key == "TITLE":
            title = value
        elif key == "SITES":
            n = int(value)
            while len(sites) < n and i < len(lines):
                if lines[i].strip():
                    sites.append(lines[i].strip())
                i += 1
        elif key.startswith("OFFSETS"):
            while len(offsets) < len(sites) and i < len(lines):
                text = lines[i].strip()
                if text:
                    try:
                        offsets.append(float(text))
                    except ValueError:
                        break
                i += 1
            break
    if tag.upper() != _DATA_TAG:
        raise FormatError(
            f"{path}: expected format {_DATA_TAG!r}, got {tag!r}"
        )
    if len(offsets) != len(sites):
        raise FormatError(
            f"{path}: {len(sites)} sites but {len(offsets)} offsets"
        )
    return OccamData(sites, np.array(offsets, dtype=float), title)


def _last_number(line: str) -> float:
    try:
        return float(line.rsplit("=", 1)[1].strip())
    except (IndexError, ValueError):
        return float("nan")


def read_log(path: str | os.PathLike[str]) -> OccamLog:
    """Read the iteration history of an Occam2D log file.

    Parameters
    ----------
    path : str or os.PathLike
        Log file (usually ``LogFile.logfile``).

    Returns
    -------
    OccamLog

    Notes
    -----
    Each iteration starts with ``** ITERATION n **``. Within it the
    last reported value wins: ``AND IS`` gives the accepted misfit,
    ``MINIMUM TOL FROM`` or ``INTERCEPT IS AT MU`` the Lagrange
    multiplier, and ``STEPSIZE IS`` and ``ROUGHNESS IS`` the step
    size and roughness.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.native.occam2d import read_log
    >>> text = (" ** ITERATION 1 **\\n AND IS = 8.9\\n"
    ...         " ROUGHNESS IS = 16.8\\n")
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = os.path.join(tmp, "LogFile.logfile")
    ...     _ = open(p, "w").write(text)
    ...     log = read_log(p)
    >>> log.iteration.tolist(), log.rms.tolist()
    ([1], [8.9])
    """
    names = ("rms", "roughness", "lagrange", "stepsize")
    records: list[dict[str, float]] = []
    current: dict[str, float] | None = None
    for raw in read_lines(path):
        text = raw.strip()
        up = text.upper()
        if "** ITERATION" in up:
            tokens = text.replace("*", "").split()
            number = -1
            for k, tok in enumerate(tokens[:-1]):
                if tok.upper() == "ITERATION":
                    try:
                        number = int(tokens[k + 1])
                    except ValueError:
                        pass
                    break
            current = dict.fromkeys(names, float("nan"))
            current["iteration"] = number
            records.append(current)
            continue
        if current is None:
            continue
        if "MINIMUM TOL FROM" in up or "INTERCEPT IS AT MU" in up:
            name = "lagrange"
        elif up.startswith("AND IS"):
            name = "rms"
        elif "STEPSIZE IS" in up:
            name = "stepsize"
        elif "ROUGHNESS IS" in up:
            name = "roughness"
        else:
            continue
        value = _last_number(text)
        if np.isfinite(value):
            current[name] = value
    records = [r for r in records if r["iteration"] >= 0]
    return OccamLog(
        iteration=np.array(
            [r["iteration"] for r in records], dtype=int
        ),
        **{
            n: np.array([r[n] for r in records], dtype=float)
            for n in names
        },
    )


def resistivity_grid(
    values: np.ndarray, model: OccamModel, mesh: OccamMesh
) -> np.ndarray:
    """Per-cell log10 resistivity from block values.

    Parameters
    ----------
    values : array_like of shape (n_params,)
        Parameter values of an iteration, log10 ohm m.
    model : OccamModel
        Block layout.
    mesh : OccamMesh
        Mesh the layout refers to.

    Returns
    -------
    ndarray of shape (n_z, n_x)
        log10 resistivity of every mesh cell; NaN for air rows and
        cells no block covers.

    Notes
    -----
    Blocks are filled row by row from the first earth row
    :math:`k_0 = n_{\\mathrm{air}}`; a block that would extend past
    the mesh is clipped. Values beyond the declared blocks are
    ignored and missing values leave cells NaN.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.native.occam2d import (OccamMesh, OccamModel,
    ...                                  resistivity_grid)
    >>> mesh = OccamMesh(np.ones(3), np.ones(2))
    >>> model = OccamModel([(2, np.array([1, 2]))])
    >>> print(resistivity_grid([1.0, 2.0], model, mesh))
    [[1. 2. 2.]
     [1. 2. 2.]]
    """
    vals = np.asarray(values, dtype=float)
    n_z, n_x = mesh.z_widths.size, mesh.x_widths.size
    grid = np.full((n_z, n_x), np.nan)
    row = int(mesh.n_air)
    p = 0
    for n_rows, cols in model.layers:
        r0, r1 = row, min(row + int(n_rows), n_z)
        row = r1
        col = 0
        for width in cols:
            c0, c1 = col, min(col + int(width), n_x)
            col = c1
            if p < vals.size:
                grid[r0:r1, c0:c1] = vals[p]
            p += 1
    return grid
