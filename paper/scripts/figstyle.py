"""Shared figure style for the PCSF Geophysics manuscript.

Conventions used by every figure script:

* Arial (Helvetica substitute), 7 pt body text, 8 pt panel labels.
* Widths: single column 89 mm, 1.5 column 120 mm, double column 183 mm.
* Resistivity: ``RES_CMAP`` maps conductive (low rho) to red and
  resistive (high rho) to blue, the usual EM/MT convention, always on
  a log10 scale.
* Differences in log10(rho): ``DIFF_CMAP`` (diverging, centred on 0),
  deliberately different from the resistivity map so that the two are
  never confused.
* Bold lowercase panel labels (a, b, c, ...) at the top-left corner.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

MM = 1.0 / 25.4
SINGLE = 89 * MM
ONEHALF = 120 * MM
DOUBLE = 183 * MM

import paths

# Outputs go to paths.FIGURES and paths.RESULTS; DATA is the folder of
# the .pcsf/.pcsm models the analyses read (paths.MODELS).
FIG = paths.FIGURES
RESULTS = paths.RESULTS
DATA = paths.MODELS
for _d in (FIG, RESULTS):
    _d.mkdir(parents=True, exist_ok=True)

RES_CMAP = mpl.colormaps["RdYlBu"]
DIFF_CMAP = mpl.colormaps["PuOr_r"]
INK = "#222222"
GREY = "#6b6b6b"
LIGHT = "#d9d9d9"

# Categorical colours (colour-blind safe, Okabe-Ito subset).
C_BLUE = "#0072B2"
C_ORANGE = "#E69F00"
C_GREEN = "#009E73"
C_RED = "#D55E00"
C_PURPLE = "#CC79A7"
C_SKY = "#56B4E9"
C_BLACK = "#000000"


def apply() -> None:
    """Apply the manuscript rcParams."""
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "DejaVu Sans"],
            "font.size": 7,
            "axes.titlesize": 7,
            "axes.labelsize": 7,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.fontsize": 6.5,
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "xtick.minor.width": 0.4,
            "ytick.minor.width": 0.4,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "xtick.minor.size": 1.5,
            "ytick.minor.size": 1.5,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "lines.linewidth": 1.0,
            "mathtext.default": "regular",
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
            "figure.dpi": 150,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def panel_label(ax, letter: str, x: float = -0.02, y: float = 1.02,
                ha: str = "right", **kw) -> None:
    """Bold lowercase panel label just outside the top-left corner."""
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=8,
            fontweight="bold", ha=ha, va="bottom", **kw)


def boxed_spines(ax) -> None:
    """Full frame (for maps and sections)."""
    for s in ("top", "right"):
        ax.spines[s].set_visible(True)


def log_rho_colorbar(fig, mappable, cax, label=r"$\rho$ ($\Omega$ m)",
                     orientation="vertical"):
    """Colorbar for a log10(rho) mappable, labelled in ohm m."""
    cb = fig.colorbar(mappable, cax=cax, orientation=orientation)
    lo, hi = mappable.get_clim()
    ticks = np.arange(np.ceil(lo), np.floor(hi) + 1e-9, 1.0)
    if ticks.size < 2:
        ticks = np.linspace(lo, hi, 3)
    cb.set_ticks(ticks)
    cb.set_ticklabels([_fmt_pow(t) for t in ticks])
    cb.set_label(label)
    cb.outline.set_linewidth(0.5)
    cb.ax.tick_params(width=0.5, length=2)
    return cb


def _fmt_pow(t: float) -> str:
    if abs(t - round(t)) < 1e-9:
        t = int(round(t))
        if 0 <= t <= 4:
            return f"{10 ** t:g}"
        return rf"$10^{{{t}}}$"
    return f"{10 ** t:.3g}"


def save(fig, name: str) -> Path:
    """Save PNG (600 dpi) preview, PDF, and editable SVG and EPS.

    SVG keeps text as text (``svg.fonttype = "none"``) so that labels
    stay editable; PDF and EPS embed TrueType fonts (type 42). Dense
    cell fields (colour meshes and collections of more than 1000
    polygons) are rasterized at the figure resolution in the vector
    files: written as vectors, a model section takes tens of MB in
    EPS, while axes, labels and annotations stay editable vectors and
    the values themselves are in the deposited models.
    """
    from matplotlib.collections import (
        PolyCollection,
        QuadMesh,
        TriMesh,
    )

    has_raster = False
    for ax in fig.axes:
        for coll in ax.collections:
            dense = isinstance(coll, (QuadMesh, TriMesh)) or (
                isinstance(coll, PolyCollection)
                and len(coll.get_paths()) > 1000
            )
            if dense:
                coll.set_rasterized(True)
                has_raster = True
    png = FIG / f"{name}.png"
    fig.savefig(png)
    fig.savefig(FIG / f"{name}.pdf")
    with mpl.rc_context({"svg.fonttype": "none"}):
        fig.savefig(FIG / f"{name}.svg")
    # EPS stores images as uncompressed ASCII hex (tens of MB for a
    # 600 dpi field), so it is written only for pure vector figures;
    # figures with raster fields keep the editable SVG.
    eps = FIG / f"{name}.eps"
    if has_raster:
        eps.unlink(missing_ok=True)
    else:
        fig.savefig(eps)
    plt.close(fig)
    return png
