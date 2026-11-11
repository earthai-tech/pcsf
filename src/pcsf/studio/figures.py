"""Matplotlib views of PCSF models for PCSF Studio.

Every geometry kind is drawn in two dimensions, in the model frame
(metres), as :math:`\\log_{10}\\rho` with :math:`\\rho` the canonical
linear resistivity in ohm m:

=================== ==========================================
Geometry kind       Views (position index runs over)
=================== ==========================================
``grid2d``          ``section``
``grid3d``          ``depth slice`` (z cells), ``x section``
                    (x cells), ``y section`` (y cells)
``mesh_unstructured`` ``mesh``
``multiline``       ``line`` (lines)
=================== ==========================================

The functions take a :class:`matplotlib.figure.Figure` and need no
Qt, so the same code draws in the application, in tests (Agg backend)
and in scripts.

Notes
-----
The default colour range is the 2nd to 98th percentile of the finite
values of :math:`\\log_{10}\\rho` below
:data:`AIR_THRESHOLD_OHM_M`, so that air cells (often
:math:`10^{11}` to :math:`10^{13}` ohm m, kept unmasked in many
files) and isolated extremes do not compress the colour scale of
the earth. Air cells are still drawn, in the colour of the upper
limit.

With ``fit=True`` the horizontal limits are the station extent,
padded on each side by 20 % of it (at least 100 m). A mesh without
stations is fitted to the 5th to 95th percentiles of its node
coordinates instead: meshes are refined under the survey, so most
nodes lie there, while the padding has few. The depth limit applies
to every view with a depth axis.

``grid3d`` models are drawn in the frame of their station table:
cell nodes plus ``geometry.origin`` (specification, ``geometry``
group). ``rotation_deg`` is not applied; the axes are the grid
axes.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.schema import PCSFModel

__all__ = [
    "AIR_THRESHOLD_OHM_M",
    "DEFAULT_CMAP",
    "VIEWS",
    "color_range",
    "draw",
    "n_positions",
    "position_label",
    "restyle",
    "view_values",
    "views",
]

#: Default colour map: low resistivity (conductors) in red.
DEFAULT_CMAP = "jet_r"

#: Resistivity (ohm m) from which values are treated as air when
#: choosing the default colour range; equal to the air threshold of
#: :func:`pcsf.adapters.modem_to_pcsf`.
AIR_THRESHOLD_OHM_M = 1e8

#: Views offered for each geometry kind.
VIEWS: dict[str, tuple[str, ...]] = {
    "grid2d": ("section",),
    "grid3d": ("depth slice", "x section", "y section"),
    "mesh_unstructured": ("mesh",),
    "multiline": ("line",),
}

_LABEL = r"$\log_{10}\rho$ ($\Omega$ m)"


def views(model: PCSFModel) -> tuple[str, ...]:
    """Views available for a model.

    Parameters
    ----------
    model : PCSFModel
        Model to draw.

    Returns
    -------
    tuple of str
        View names, the first one being the default.

    Examples
    --------
    >>> from pcsf import datasets
    >>> from pcsf.studio.sources import open_source
    >>> from pcsf.studio.figures import views
    >>> views(open_source(datasets.path("modem_tiny")).model)
    ('depth slice', 'x section', 'y section')
    """
    return VIEWS[model.kind]


def _check_view(model: PCSFModel, view: str) -> None:
    if view not in VIEWS[model.kind]:
        raise ValueError(
            f"view {view!r} is not available for {model.kind!r} "
            f"models; use one of {VIEWS[model.kind]}"
        )


def n_positions(model: PCSFModel, view: str) -> int:
    """Number of positions (slices, sections or lines) of a view.

    Parameters
    ----------
    model : PCSFModel
        Model to draw.
    view : str
        One of :func:`views` (*model*).

    Returns
    -------
    int
        1 for views without a position, else the number of cells
        along the sliced axis or the number of lines.

    Raises
    ------
    ValueError
        If *view* is not available for the model.
    """
    _check_view(model, view)
    shape = np.shape(model.resistivity)
    if view == "depth slice":
        return shape[0]
    if view == "y section":
        return shape[1]
    if view == "x section":
        return shape[2]
    if view == "line":
        return len(model.geometry.lines)
    return 1


def position_label(model: PCSFModel, view: str, index: int) -> str:
    """Text describing a position, such as ``"z = 125 m"``.

    Parameters
    ----------
    model : PCSFModel
        Model to draw.
    view : str
        One of :func:`views` (*model*).
    index : int
        Position, ``0 <= index < n_positions(model, view)``.

    Returns
    -------
    str
        Label of the position; empty for views without one.
    """
    _check_view(model, view)
    g = model.geometry
    if view == "depth slice":
        return f"z = {g.z[index]:.6g} m"
    ox, oy = _offset(model)
    if view == "y section":
        return f"y = {g.y[index] + oy:.6g} m"
    if view == "x section":
        return f"x = {g.x[index] + ox:.6g} m"
    if view == "line":
        return f"line {g.lines[index].line_id}"
    return ""


def _offset(model: PCSFModel) -> tuple[float, float]:
    """Horizontal origin of a ``grid3d`` model, else zeros."""
    origin = getattr(model.geometry, "origin", None)
    if model.kind != "grid3d" or origin is None:
        return 0.0, 0.0
    origin = np.ravel(np.asarray(origin, dtype=float))
    return float(origin[0]), float(origin[1])


def view_values(
    model: PCSFModel, view: str | None = None, index: int = 0
) -> np.ndarray:
    """Resistivity values shown by a view, flattened.

    Parameters
    ----------
    model : PCSFModel
        Model drawn.
    view : str, optional
        One of :func:`views` (*model*); the first one by default.
    index : int, default 0
        Position of the slice, section or line; clipped to the
        valid range.

    Returns
    -------
    ndarray of float, shape (n,)
        Linear resistivity (ohm m) of the cells of the view: one
        depth slice or section of a ``grid3d`` model, one line of a
        ``multiline`` model, the whole model otherwise.

    Raises
    ------
    ValueError
        If *view* is not available for the model.

    Examples
    --------
    >>> from pcsf import datasets
    >>> from pcsf.studio.sources import open_source
    >>> from pcsf.studio.figures import view_values
    >>> m = open_source(datasets.path("modem_tiny")).model
    >>> view_values(m, "depth slice", 0).shape
    (20,)
    """
    view = view or views(model)[0]
    _check_view(model, view)
    index = int(np.clip(index, 0, n_positions(model, view) - 1))
    if view == "line":
        rho = model.geometry.lines[index].resistivity
    else:
        rho = np.asarray(model.resistivity)
        if view == "depth slice":
            rho = rho[index]
        elif view == "y section":
            rho = rho[:, index, :]
        elif view == "x section":
            rho = rho[:, :, index]
    return np.ravel(np.asarray(rho, dtype=float))


def _log10(values: Any) -> np.ndarray:
    rho = np.asarray(values, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.log10(rho)
    out[~np.isfinite(out)] = np.nan
    return out


def _model_values(model: PCSFModel) -> np.ndarray:
    if model.kind == "multiline":
        parts = [np.ravel(e.resistivity) for e in model.geometry.lines]
        return np.concatenate(parts) if parts else np.array([])
    return np.ravel(model.resistivity)


def color_range(
    model: PCSFModel, percentiles: tuple[float, float] = (2.0, 98.0)
) -> tuple[float, float]:
    """Default colour range of a model in :math:`\\log_{10}\\rho`.

    Parameters
    ----------
    model : PCSFModel
        Model to draw.
    percentiles : tuple of float, default (2, 98)
        Lower and upper percentiles of the finite values.

    Returns
    -------
    tuple of float
        ``(vmin, vmax)``; ``(0, 1)`` when the model has no finite
        positive value below :data:`AIR_THRESHOLD_OHM_M`, and
        widened by 0.5 on each side when all values are equal.

    Examples
    --------
    >>> from pcsf import datasets
    >>> from pcsf.studio.sources import open_source
    >>> from pcsf.studio.figures import color_range
    >>> m = open_source(datasets.path("occam2d_tiny")).model
    >>> lo, hi = color_range(m)
    >>> bool(lo < hi)
    True
    """
    vals = _log10(_model_values(model))
    vals = vals[
        np.isfinite(vals) & (vals < np.log10(AIR_THRESHOLD_OHM_M))
    ]
    if vals.size == 0:
        return 0.0, 1.0
    lo, hi = np.percentile(vals, percentiles)
    if hi <= lo:
        lo, hi = lo - 0.5, hi + 0.5
    return float(lo), float(hi)


def _edges(centres: Any, nodes: Any = None) -> np.ndarray:
    """Cell edges: the nodes when given, else midpoints of centres."""
    if nodes is not None and np.size(nodes) == np.size(centres) + 1:
        return np.asarray(nodes, dtype=float)
    c = np.asarray(centres, dtype=float)
    if c.size == 1:
        return np.array([c[0] - 0.5, c[0] + 0.5])
    mid = (c[:-1] + c[1:]) / 2.0
    return np.concatenate(
        [[2 * c[0] - mid[0]], mid, [2 * c[-1] - mid[-1]]]
    )


def _stations(model: PCSFModel):
    st = model.stations
    if st is None or st.x is None or len(st.name) == 0:
        return None
    return st


def _padded(
    values: Any, frac: float = 0.2, least: float = 100.0
) -> tuple[float, float] | None:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    lo, hi = float(v.min()), float(v.max())
    pad = max(frac * (hi - lo), least)
    return lo - pad, hi + pad


def _limits(ax, model, view, index, max_depth, fit) -> None:
    """Apply the depth limit and the fit to the survey."""
    depth_axis = view != "depth slice"
    limited = depth_axis and max_depth is not None and max_depth > 0
    bottom, top = ax.get_ylim()
    if view == "mesh":
        # Meshes extend far into the air; the earth starts at depth 0
        # or at the highest node below it.
        nodes = np.asarray(model.geometry.nodes, dtype=float)
        if fit:
            z_lo, z_hi = np.percentile(nodes[:, 1], (5.0, 95.0))
            top = min(z_lo, 0.0)
            bottom = z_hi
        if limited:
            top = max(top, min(0.0, bottom))
    if limited:
        bottom = min(max_depth, bottom)
    ax.set_ylim(bottom, top) if depth_axis else None
    if not fit:
        return
    st = _stations(model)
    if view == "mesh" and st is None:
        lo, hi = np.percentile(nodes[:, 0], (5.0, 95.0))
        ax.set_xlim(lo, hi)
        return
    if st is None:
        return
    x = np.asarray(st.x, dtype=float)
    if view == "line" and st.line_id is not None:
        line = model.geometry.lines[index].line_id
        x = x[np.asarray(st.line_id) == line]
    if view == "x section":
        span = _padded(st.y) if st.y is not None else None
    else:
        span = _padded(x)
    if span is not None:
        ax.set_xlim(*span)
    if view == "depth slice" and st.y is not None:
        span_y = _padded(st.y)
        if span_y is not None:
            ax.set_ylim(*span_y)


def restyle(
    fig: Any,
    *,
    ink: str = "#1f2533",
    background: str = "#ffffff",
    muted: str | None = None,
) -> None:
    """Recolour a drawn figure for a light or dark background.

    Only colours change: the figure and axes backgrounds, the axes
    lines, ticks, labels and titles, and the station markers. The
    colour-mapped artists are left as drawn.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure drawn by :func:`draw` (or any figure).
    ink : str, default "#1f2533"
        Colour of the text, the ticks and the station markers.
    background : str, default "#ffffff"
        Colour of the figure and of the axes.
    muted : str, optional
        Colour of the axes lines; *ink* by default.

    Notes
    -----
    Station markers are the lines without a connecting segment
    (line style ``"None"``); lines with a segment keep their
    colour.

    Examples
    --------
    >>> import matplotlib
    >>> matplotlib.use("Agg")
    >>> from matplotlib.figure import Figure
    >>> from pcsf import datasets
    >>> from pcsf.studio.sources import open_source
    >>> from pcsf.studio.figures import draw, restyle
    >>> fig = Figure()
    >>> m = open_source(datasets.path("occam2d_tiny")).model
    >>> ax = draw(fig, m)
    >>> restyle(fig, ink="#e6e9f2", background="#1b1f2b")
    >>> ax.title.get_color()
    '#e6e9f2'
    """
    edge = ink if muted is None else muted
    fig.set_facecolor(background)
    for ax in fig.axes:
        ax.set_facecolor(background)
        for spine in ax.spines.values():
            spine.set_edgecolor(edge)
        ax.tick_params(colors=ink, which="both")
        for text in (ax.title, ax.xaxis.label, ax.yaxis.label):
            text.set_color(ink)
        for line in ax.lines:
            if line.get_linestyle() == "None":
                line.set_color(ink)
        legend = ax.get_legend()
        if legend is not None:
            for text in legend.get_texts():
                text.set_color(ink)
    for text in fig.texts:
        text.set_color(ink)


def _section(ax, x_edges, z_edges, values, norm, cmap):
    mesh = ax.pcolormesh(
        x_edges,
        z_edges,
        _log10(values),
        cmap=cmap,
        norm=norm,
        shading="flat",
    )
    ax.set_ylim(z_edges.max(), z_edges.min())
    return mesh


def draw(
    fig: Any,
    model: PCSFModel,
    view: str | None = None,
    index: int = 0,
    *,
    cmap: str = DEFAULT_CMAP,
    vmin: float | None = None,
    vmax: float | None = None,
    show_stations: bool = True,
    max_depth: float | None = None,
    fit: bool = False,
    title: str | None = None,
) -> Any:
    """Draw one view of a model on a figure.

    The figure is cleared, then gets one axes with the view and a
    colour bar of :math:`\\log_{10}\\rho`. Missing values (NaN, for
    example masked air cells) are left blank.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to draw on.
    model : PCSFModel
        Model to draw.
    view : str, optional
        One of :func:`views` (*model*); the first one by default.
    index : int, default 0
        Position of the slice, section or line; clipped to the
        valid range.
    cmap : str, default DEFAULT_CMAP
        Matplotlib colour map name.
    vmin, vmax : float, optional
        Colour range in :math:`\\log_{10}\\rho`; from
        :func:`color_range` when not given.
    show_stations : bool, default True
        Mark the stations (triangles at the top of sections, dots
        on depth slices) when the model has a station table.
    max_depth : float, optional
        Largest depth shown (m) on views with a depth axis; the
        whole model when None or not positive.
    fit : bool, default False
        Limit the horizontal axes to the survey (see Notes).
    title : str, optional
        Axes title; the view and position by default.

    Returns
    -------
    matplotlib.axes.Axes
        The axes of the view.

    Raises
    ------
    ValueError
        If *view* is not available for the model.

    Examples
    --------
    >>> import matplotlib
    >>> matplotlib.use("Agg")
    >>> from matplotlib.figure import Figure
    >>> from pcsf import datasets
    >>> from pcsf.studio.sources import open_source
    >>> from pcsf.studio.figures import draw
    >>> m = open_source(datasets.path("modem_tiny")).model
    >>> ax = draw(Figure(), m, "x section", index=2)
    >>> ax.get_xlabel(), ax.get_ylabel()
    ('y (m)', 'depth (m)')
    """
    from matplotlib.colors import Normalize

    view = view or views(model)[0]
    _check_view(model, view)
    index = int(np.clip(index, 0, n_positions(model, view) - 1))
    if vmin is None or vmax is None:
        lo, hi = color_range(model)
        vmin = lo if vmin is None else vmin
        vmax = hi if vmax is None else vmax
    norm = Normalize(vmin=vmin, vmax=vmax)
    fig.clear()
    ax = fig.add_subplot(1, 1, 1)
    g = model.geometry
    st = _stations(model) if show_stations else None
    rho = np.asarray(model.resistivity) if view != "line" else None

    if view in ("section", "line"):
        if view == "line":
            entry = g.lines[index]
            g2, rho = entry.geometry, np.asarray(entry.resistivity)
            if st is not None and st.line_id is not None:
                keep = np.asarray(st.line_id) == entry.line_id
                st_x = np.asarray(st.x)[keep]
            else:
                st_x = None
        else:
            g2 = g
            st_x = None if st is None else np.asarray(st.x)
        xe, ze = _edges(g2.x, g2.x_nodes), _edges(g2.z, g2.z_nodes)
        artist = _section(ax, xe, ze, rho, norm, cmap)
        if st_x is not None and st_x.size:
            ax.plot(
                st_x,
                np.full(st_x.shape, ze.min()),
                "kv",
                ms=5,
                clip_on=False,
            )
        ax.set_xlabel("x (m)")
        ax.set_ylabel("depth (m)")
    elif view == "depth slice":
        ox, oy = _offset(model)
        xe = _edges(g.x, g.x_nodes) + ox
        ye = _edges(g.y, g.y_nodes) + oy
        artist = ax.pcolormesh(
            xe,
            ye,
            _log10(rho[index]),
            cmap=cmap,
            norm=norm,
            shading="flat",
        )
        if st is not None and st.y is not None:
            ax.plot(st.x, st.y, "k.", ms=4)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        ax.set_aspect("equal", adjustable="box")
    elif view == "x section":
        ye = _edges(g.y, g.y_nodes) + _offset(model)[1]
        ze = _edges(g.z, g.z_nodes)
        artist = _section(ax, ye, ze, rho[:, :, index], norm, cmap)
        ax.set_xlabel("y (m)")
        ax.set_ylabel("depth (m)")
    elif view == "y section":
        xe = _edges(g.x, g.x_nodes) + _offset(model)[0]
        ze = _edges(g.z, g.z_nodes)
        artist = _section(ax, xe, ze, rho[:, index, :], norm, cmap)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("depth (m)")
    else:  # mesh
        nodes = np.asarray(g.nodes, dtype=float)
        artist = ax.tripcolor(
            nodes[:, 0],
            nodes[:, 1],
            np.asarray(g.connectivity),
            facecolors=_log10(rho),
            cmap=cmap,
            norm=norm,
            edgecolors="none",
        )
        ax.set_ylim(nodes[:, 1].max(), nodes[:, 1].min())
        first, second = g.plane[0], g.plane[1]
        ax.set_xlabel(f"{first} (m)")
        ax.set_ylabel(
            "depth (m)" if second == "z" else f"{second} (m)"
        )

    _limits(ax, model, view, index, max_depth, fit)
    # A colorbar made with ``ax=ax`` anchors the plot to its right
    # edge (``panchor``), which leaves the left of a wide canvas
    # empty for equal-aspect views. An inset keeps the colorbar
    # next to the plot, and both stay centred at any width; the
    # constrained layout still makes room for its label.
    cax = ax.inset_axes((1.03, 0.0, 0.035, 1.0))
    fig.colorbar(artist, cax=cax, label=_LABEL)
    label = position_label(model, view, index)
    ax.set_title(
        title
        if title is not None
        else f"{view}" + (f", {label}" if label else "")
    )
    return ax
