"""Parsers of ModEM files.

ModEM [1]_ stores a 3-D resistivity model in a text ``.rho`` file
(Weerachai Siripunvaraporn's WS format), the data and station
positions in a ``.dat`` file, and the progress of a non-linear
conjugate-gradient inversion in a log file. The functions here read
them with NumPy only.

Notes
-----
A ``.rho`` file has one header line, a control line
``nx ny nz n_air TYPE`` with ``TYPE`` in ``LOGE``, ``LOG10`` or
``LINEAR``, the cell widths along :math:`x` (north), :math:`y`
(east) and :math:`z` (down), then :math:`n_z n_y` rows of
:math:`n_x` values with :math:`x` running from north to south. An
optional trailer gives the grid origin (2 or 3 values, metres) and
a rotation angle. Without a trailer the grid is centred
horizontally on the origin and its top is at :math:`z = 0`.

Values are returned as natural logarithms,
:math:`\\ln\\rho = \\ln(10)\\,\\log_{10}\\rho`, with axis order
``(z, y, x)`` and :math:`x` increasing northward.

References
----------
.. [1] Kelbert, A., N. Meqbel, G. D. Egbert, and K. Tandon, 2014,
   ModEM: A modular system for inversion of electromagnetic
   geophysical data: Computers & Geosciences, 66, 40-53.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import numpy as np

from ..exceptions import FormatError
from ._tokens import read_lines

__all__ = [
    "ModemData",
    "ModemLog",
    "ModemModel",
    "read_data",
    "read_log",
    "read_model",
]


@dataclass
class ModemModel:
    """ModEM 3-D resistivity model.

    Attributes
    ----------
    x_widths, y_widths, z_widths : ndarray
        Cell widths, metres; :math:`x` north, :math:`y` east,
        :math:`z` down.
    log_rho : ndarray of shape (n_z, n_y, n_x)
        :math:`\\ln\\rho`, :math:`x` increasing northward.
    n_air : int
        Air layers declared in the control line.
    log_type : str
        Encoding declared in the file.
    origin : ndarray of shape (3,)
        Model origin, metres.
    rotation : float
        Grid rotation, degrees.
    """

    x_widths: np.ndarray
    y_widths: np.ndarray
    z_widths: np.ndarray
    log_rho: np.ndarray
    n_air: int = 0
    log_type: str = "LOGE"
    origin: np.ndarray = field(default_factory=lambda: np.zeros(3))
    rotation: float = 0.0

    @staticmethod
    def _nodes(widths: np.ndarray) -> np.ndarray:
        return np.concatenate([[0.0], np.cumsum(widths)])

    @property
    def x_nodes(self) -> np.ndarray:
        """Cell edges along x, metres, from zero."""
        return self._nodes(self.x_widths)

    @property
    def y_nodes(self) -> np.ndarray:
        """Cell edges along y, metres, from zero."""
        return self._nodes(self.y_widths)

    @property
    def z_nodes(self) -> np.ndarray:
        """Cell edges along z, metres, from zero."""
        return self._nodes(self.z_widths)


@dataclass
class ModemData:
    """Stations of a ModEM data file.

    Attributes
    ----------
    sites : list of str
        Station codes in order of first appearance.
    xyz : ndarray of shape (n_sites, 3)
        Model-frame station coordinates, metres.
    lonlat : ndarray of shape (n_sites, 2)
        Longitude and latitude; NaN when the file gives zeros.
    comment : str
        ``#`` comment lines joined by newlines.
    """

    sites: list[str]
    xyz: np.ndarray
    lonlat: np.ndarray
    comment: str = ""


@dataclass
class ModemLog:
    """Iteration history of a ModEM NLCG log file.

    Attributes
    ----------
    iteration : ndarray of int
        0 for the starting model, then completed iterations.
    objective, model_norm, rms, lagrange, alpha : ndarray
        Objective function, model norm, RMS misfit, damping
        parameter :math:`\\lambda` and line-search step.
    """

    iteration: np.ndarray
    objective: np.ndarray
    model_norm: np.ndarray
    rms: np.ndarray
    lagrange: np.ndarray
    alpha: np.ndarray


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def read_model(path: str | os.PathLike[str]) -> ModemModel:
    """Read a ModEM 3-D ``.rho`` model file.

    Parameters
    ----------
    path : str or os.PathLike
        Model file.

    Returns
    -------
    ModemModel

    Raises
    ------
    FormatError
        If the control line or the value block cannot be read.

    Notes
    -----
    The first line is always skipped, as ModEM's own reader does.
    ``LOG10`` values are converted with :math:`\\ln 10`; ``LINEAR``
    values with :math:`\\ln`, non-positive values becoming NaN.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.native.modem import read_model
    >>> text = ("# tiny\\n2 1 1 0 LOGE\\n10 20\\n30\\n40\\n"
    ...         "4.0 5.0\\n")
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = os.path.join(tmp, "m.rho")
    ...     _ = open(p, "w").write(text)
    ...     m = read_model(p)
    >>> m.log_rho.tolist(), m.origin.tolist()
    ([[[5.0, 4.0]]], [-15.0, -15.0, 0.0])
    """
    lines = read_lines(path)
    i = 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    try:
        ctrl = lines[i].split()
        nx, ny, nz = (int(v) for v in ctrl[:3])
    except (IndexError, ValueError) as exc:
        raise FormatError(f"{path}: cannot read control line") from exc
    i += 1
    has_air = len(ctrl) > 3 and ctrl[3].lstrip("-").isdigit()
    n_air = int(ctrl[3]) if has_air else 0
    log_type = "LOGE"
    for tok in ctrl:
        if tok.isalpha() or tok.upper() in ("LOGE", "LOG10", "LINEAR"):
            log_type = tok.upper()
    widths: list[float] = []
    target = nx + ny + nz
    while i < len(lines) and len(widths) < target:
        text = lines[i].strip()
        i += 1
        if text and not text.startswith("#"):
            widths.extend(
                float(t) for t in text.split() if _is_number(t)
            )
    total = nx * ny * nz
    values: list[float] = []
    while i < len(lines) and len(values) < total:
        text = lines[i].strip()
        i += 1
        if not text or text.startswith("#"):
            continue
        parts = text.split()
        # A row always has nx values; a shorter numeric line near the
        # end is the origin trailer.
        if len(parts) < nx and all(_is_number(p) for p in parts):
            if len(values) >= total - nx:
                i -= 1
                break
        values.extend(float(t) for t in parts if _is_number(t))
    if len(widths) < target or len(values) < total:
        raise FormatError(
            f"{path}: expected {target} widths and {total} values, "
            f"got {len(widths)} and {len(values)}"
        )
    xw = np.array(widths[:nx])
    yw = np.array(widths[nx : nx + ny])
    zw = np.array(widths[nx + ny : target])
    # Rows run from north to south; flip so that x increases north.
    arr = np.array(values[:total]).reshape(nz, ny, nx)[:, :, ::-1]
    arr = arr.copy()
    origin = np.array([-xw.sum() / 2.0, -yw.sum() / 2.0, 0.0])
    rotation = 0.0
    trailer = [
        t.strip()
        for t in lines[i:]
        if t.strip() and not t.strip().startswith("#")
    ]
    if trailer:
        first = trailer[0].split()
        if 2 <= len(first) <= 3 and all(_is_number(p) for p in first):
            vals = [float(p) for p in first] + [0.0] * (3 - len(first))
            origin = np.array(vals)
            if len(trailer) > 1:
                second = trailer[1].split()
                if len(second) == 1 and _is_number(second[0]):
                    rotation = float(second[0])
    if log_type == "LOG10":
        log_rho = arr * np.log(10.0)
    elif log_type == "LINEAR":
        with np.errstate(divide="ignore", invalid="ignore"):
            log_rho = np.log(np.where(arr > 0, arr, np.nan))
    else:
        log_rho = arr
    return ModemModel(
        xw, yw, zw, log_rho, n_air, log_type, origin, rotation
    )


def read_data(path: str | os.PathLike[str]) -> ModemData:
    """Read the stations of a ModEM ``.dat`` data file.

    Parameters
    ----------
    path : str or os.PathLike
        Data file.

    Returns
    -------
    ModemData
        Stations in order of first appearance, with the coordinates
        of their first data row.

    Raises
    ------
    FormatError
        If the file contains no data row.

    Notes
    -----
    Data rows have at least 11 columns: period, code, latitude,
    longitude, :math:`x`, :math:`y`, :math:`z`, component, real and
    imaginary parts, error. A latitude and longitude of exactly zero
    mean unknown.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.native.modem import read_data
    >>> row = "1.0 S1 25.0 117.0 10 20 0 ZXY 1 1 0.1\\n"
    >>> head = ("# demo\\n> Off_Diagonal_Impedance\\n> exp(+i w t)\\n"
    ...         "> [mV/km]/[nT]\\n> 0.0\\n> 0 0\\n> 1 1\\n")
    >>> text = head + row
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = os.path.join(tmp, "d.dat")
    ...     _ = open(p, "w").write(text)
    ...     d = read_data(p)
    >>> d.sites, d.xyz.tolist(), d.lonlat.tolist()
    (['S1'], [[10.0, 20.0, 0.0]], [[117.0, 25.0]])
    """
    lines = read_lines(path)
    comments: list[str] = []
    sites: list[str] = []
    xyz: list[tuple[float, float, float]] = []
    lonlat: list[tuple[float, float]] = []
    seen: set[str] = set()
    for raw in lines:
        text = raw.strip()
        if not text:
            continue
        if text.startswith("#"):
            comments.append(text[1:].strip())
            continue
        if text.startswith(">"):
            continue
        parts = text.split()
        if len(parts) < 11 or not _is_number(parts[0]):
            continue
        code = parts[1]
        if code in seen:
            continue
        seen.add(code)
        sites.append(code)
        xyz.append(tuple(float(v) for v in parts[4:7]))
        try:
            lat, lon = float(parts[2]), float(parts[3])
        except ValueError:
            lat = lon = 0.0
        if lat == 0.0 and lon == 0.0:
            lonlat.append((np.nan, np.nan))
        else:
            lonlat.append((lon, lat))
    if not sites:
        raise FormatError(f"{path}: no ModEM data row found")
    return ModemData(
        sites,
        np.array(xyz, dtype=float),
        np.array(lonlat, dtype=float),
        "\n".join(comments),
    )


_NUM = r"([\d.E+\-]+)"
_VALUES = re.compile(
    rf"f=\s*{_NUM}\s+m2=\s*{_NUM}\s+rms=\s*{_NUM}"
    rf"\s+lambda=\s*{_NUM}\s+alpha=\s*{_NUM}",
    re.IGNORECASE,
)
_COMPLETED = re.compile(
    r"Completed\s+NLCG\s+iteration\s+(\d+)", re.IGNORECASE
)


def read_log(path: str | os.PathLike[str]) -> ModemLog:
    """Read the iteration history of a ModEM NLCG log.

    Parameters
    ----------
    path : str or os.PathLike
        Log file.

    Returns
    -------
    ModemLog

    Notes
    -----
    The ``START:`` line gives iteration 0. After each
    ``Completed NLCG iteration n`` line, the next ``with:`` line
    gives the values accepted for iteration :math:`n`.

    Examples
    --------
    >>> import os, tempfile
    >>> from pcsf.native.modem import read_log
    >>> v = "f= 95.0 m2= 0.0 rms= 9.7 lambda= 10.0 alpha= 2.0"
    >>> text = (f" START: {v}\\n Completed NLCG iteration 1\\n"
    ...         f" with: {v.replace('9.7', '5.1')}\\n")
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     p = os.path.join(tmp, "nlcg.log")
    ...     _ = open(p, "w").write(text)
    ...     log = read_log(p)
    >>> log.iteration.tolist(), log.rms.tolist()
    ([0, 1], [9.7, 5.1])
    """
    records: list[tuple[float, ...]] = []
    pending: int | None = None
    for line in read_lines(path):
        if "START:" in line.upper() and not records:
            m = _VALUES.search(line)
            if m:
                records.append((0, *map(float, m.groups())))
            continue
        m = _COMPLETED.search(line)
        if m:
            pending = int(m.group(1))
            continue
        if pending is not None and "with:" in line.lower():
            m = _VALUES.search(line)
            if m:
                records.append((pending, *map(float, m.groups())))
                pending = None
    arr = np.array(records, dtype=float).reshape(-1, 6)
    return ModemLog(
        iteration=arr[:, 0].astype(int),
        objective=arr[:, 1],
        model_norm=arr[:, 2],
        rms=arr[:, 3],
        lagrange=arr[:, 4],
        alpha=arr[:, 5],
    )
