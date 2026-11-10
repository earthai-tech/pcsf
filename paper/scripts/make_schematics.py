"""Schematic figure of the PCSF Geophysics manuscript.

Produces, in the figure folder (PNG, PDF, SVG and EPS):

  schematics  three panels, in the order the manuscript cites them:
              (a) the EM data chain and the position of PCSF;
              (b) the logical data model and its two encodings, with
                  the symbols of the formal definition;
              (c) the reference implementation: adapters, common
                  model, encodings and consumers.

Colors: blue for existing community standards, orange for what PCSF
introduces, grey for everything else (colorblind-safe pastels with a
common dark outline). The canvas is in millimetres at print size
(183 mm, double column), so font sizes are the printed sizes.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

import figstyle as fs

STD = "#d6e6f4"    # existing community standard
NEW = "#fbdcc4"    # introduced by PCSF
NEU = "#efefef"    # neither
EDGE = "#3c3c3c"
HEAD = 7.4         # box headings (pt)
BODY = 6.4         # box text (pt)
W_MM, H_MM = 183.0, 171.0


def box(ax, x, y, w, h, text, fc, size=BODY, bold=False, title=None,
        lw=0.6):
    """Rounded box; *title* is drawn bold above the body text."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
        fc=fc, ec=EDGE, lw=lw))
    cx, cy = x + w / 2, y + h / 2
    if title is None:
        ax.text(cx, cy, text, ha="center", va="center", fontsize=size,
                fontweight="bold" if bold else "normal",
                linespacing=1.3)
        return
    ax.text(cx, y + h - 2.3, title, ha="center", va="top",
            fontsize=HEAD, fontweight="bold")
    ax.text(cx, (y + h - 6.2 + y) / 2, text, ha="center", va="center",
            fontsize=size, linespacing=1.35)


def arrow(ax, p0, p1, both=False, color=EDGE, lw=0.6):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="<|-|>" if both else "-|>",
        mutation_scale=6, lw=lw, color=color, shrinkA=0, shrinkB=0))


def panel_title(ax, x, y, letter, text):
    ax.text(x, y, letter, fontsize=8.5, fontweight="bold", va="baseline")
    ax.text(x + 4.2, y, text, fontsize=7.4, va="baseline")


def data_chain(ax, top):
    """Panel a: from time series to interpretation."""
    panel_title(ax, 2, top, "a", "Where PCSF sits in the electromagnetic "
                "data chain")
    stages = [
        ("Time series", "MTH5", STD),
        ("Transfer functions", "EDI, EMTF XML", STD),
        ("Inversion", "Occam2D, ModEM,\nMARE2DEM, learned", NEU),
        ("Resistivity model", "PCSF and PCSM\n(this paper)", NEW),
        ("Interpretation, reuse", "comparison, viewers,\narchives", NEU),
    ]
    w, g, x0, y0, h = 30.0, 6.25, 4.0, top - 17.0, 12.0
    for i, (name, std, fc) in enumerate(stages):
        x = x0 + i * (w + g)
        box(ax, x, y0, w, h, name, fc, size=HEAD - 0.2, bold=True,
            lw=0.9 if fc == NEW else 0.6)
        ax.text(x + w / 2, y0 - 1.8, std, ha="center", va="top",
                fontsize=BODY, color=fs.GREY, linespacing=1.3)
        if i < len(stages) - 1:
            arrow(ax, (x + w + 0.6, y0 + h / 2),
                  (x + w + g - 0.6, y0 + h / 2))
    ly = y0 - 14.5
    for i, (fc, text) in enumerate(((STD, "community exchange standard"),
                                    (NEW, "introduced in this paper"))):
        lx = x0 + i * 52
        ax.add_patch(FancyBboxPatch((lx, ly), 4.0, 2.6,
                                    boxstyle="round,pad=0,rounding_size=0.5",
                                    fc=fc, ec=EDGE, lw=0.5))
        ax.text(lx + 5.5, ly + 1.3, text, va="center", fontsize=BODY)


def data_model(ax, top):
    """Panel b: the model of equation (model) and its encodings."""
    panel_title(ax, 2, top, "b", "Logical data model and its two "
                "encodings")
    rw, rh = 112.0, 11.0
    rx, ry = (W_MM - rw) / 2, top - 14.0
    box(ax, rx, ry, rw, rh,
        r"$M = (\kappa,\ \mathcal{G},\ \boldsymbol{\rho},\ \mathbf{r},"
        r"\ e,\ \mathbf{U},\ \mathcal{T},\ \mathcal{H},\ \mathcal{I},"
        r"\ v)$" "\nversion $v$, producing code, unit ($\\Omega$ m), "
        "coordinate reference system", NEW, size=6.8, lw=0.9)
    kids = [
        (r"Geometry $\mathcal{G}$",
         r"kind $\kappa \in \{\mathsf{G}_2, \mathsf{G}_3,"
         r" \mathsf{T}, \mathsf{L}\}$" "\n" r"cells $\Omega_c$, nodes"
         "\norigin, rotation"),
        (r"Field $\boldsymbol{\rho}$",
         r"canonical $\rho$ ($\Omega$ m)" "\n" r"source $\mathbf{r}$,"
         r" encoding $e$" "\n" r"uncertainty $\mathbf{U}$"),
        (r"Stations $\mathcal{T}$",
         "name, $x$, $y$, $z$\nline identifier\nlongitude, latitude"),
        (r"Topography $\mathcal{H}$",
         "per station\nor raster surface"),
        (r"Record $\mathcal{I}$",
         "data, errors, solver\nregularization, misfit\n"
         "depth of investigation"),
    ]
    w, g, x0, h = 32.0, 3.75, 4.0, 21.0
    y = ry - 7.5 - h
    for i, (title, text) in enumerate(kids):
        x = x0 + i * (w + g)
        box(ax, x, y, w, h, text, NEU, title=title)
        ax.plot([x + w / 2, x + w / 2], [y + h, ry - 3.75], color=EDGE,
                lw=0.6)
        if i == 0:
            ax.plot([x + w / 2, x0 + 4 * (w + g) + w / 2],
                    [ry - 3.75, ry - 3.75], color=EDGE, lw=0.6)
    ax.plot([W_MM / 2, W_MM / 2], [ry, ry - 3.75], color=EDGE, lw=0.6)
    ey, eh, ew = y - 16.0, 10.0, 52.0
    ax.plot([4, W_MM - 4], [y - 3.5, y - 3.5], color=fs.LIGHT, lw=0.6,
            ls=(0, (3, 2)))
    lx, rx2 = W_MM / 2 - ew - 14, W_MM / 2 + 14
    box(ax, lx, ey, ew, eh, "HDF5, binary, compressed", NEW,
        title="PCSF", lw=0.9)
    box(ax, rx2, ey, ew, eh, "plain text, comments allowed", NEW,
        title="PCSM", lw=0.9)
    arrow(ax, (lx + ew + 1.0, ey + eh / 2), (rx2 - 1.0, ey + eh / 2),
          both=True)
    ax.text(W_MM / 2, ey + eh / 2 + 1.6, "lossless, bit-exact",
            ha="center", va="bottom", fontsize=BODY)


def architecture(ax, top):
    """Panel c: adapters, common model, encodings and consumers."""
    panel_title(ax, 2, top, "c", "Reference implementation (pcsf)")
    hy = top - 6.0
    for x, text in ((17, "Solver output"), (52, "Adapters"),
                    (99, "Common model"), (133, "Encodings"),
                    (163, "Consumers")):
        ax.text(x, hy, text, ha="center", fontsize=HEAD,
                fontweight="bold")
    srcs = ["Occam2D", "ModEM 3D", "MARE2DEM", "EMC netCDF",
            "learned predictor,\nother codes"]
    adps = ["occam2d_to_pcsf", "modem_to_pcsf", "mare2dem_to_pcsf",
            "emc_to_pcsf", "plugin adapters"]
    rows = [hy - 7.5 - k * 10.5 for k in range(5)]
    h = 8.0
    for yc, s, a in zip(rows, srcs, adps):
        box(ax, 4, yc - h / 2, 26, h, s, NEU)
        box(ax, 36, yc - h / 2, 32, h, a, STD if False else NEU)
        ax.texts[-1].set_family("monospace")
        ax.texts[-1].set_fontsize(6.0)
        arrow(ax, (30.6, yc), (35.4, yc))
        # adapters join a bus that feeds the common model
        ax.plot([68.0, 74.0], [yc, yc], color=EDGE, lw=0.6)
    cy0, cy1 = rows[-1] - h / 2, rows[0] + h / 2
    ax.plot([74.0, 74.0], [rows[-1], rows[0]], color=EDGE, lw=0.6)
    arrow(ax, (74.0, (rows[0] + rows[-1]) / 2),
          (79.4, (rows[0] + rows[-1]) / 2))
    box(ax, 80, cy0, 38, cy1 - cy0,
        r"canonical field $\rho = C_e(r)$" "\n"
        r"node projection $\Pi_g$" "\n"
        "geometry kind declared\n"
        "conformance C1$-$C10\n"
        "inversion record", NEW, title="PCSF model", lw=0.9)
    ex, ew, eh = 124, 18, 9.0
    mid = (cy0 + cy1) / 2
    box(ax, ex, mid + 4, ew, eh, ".pcsf\n(HDF5)", NEW, lw=0.9)
    box(ax, ex, mid - 4 - eh, ew, eh, ".pcsm\n(text)", NEW, lw=0.9)
    arrow(ax, (118.6, mid + 4 + eh / 2), (ex - 0.6, mid + 4 + eh / 2),
          both=True)
    arrow(ax, (118.6, mid - 4 - eh / 2), (ex - 0.6, mid - 4 - eh / 2),
          both=True)
    arrow(ax, (ex + ew / 2, mid + 3.4), (ex + ew / 2, mid - 3.4),
          both=True)
    cons = [r"sampling, comparison" "\n" r"$\mathcal{S}_M$,"
            r" $\varepsilon$, $\beta$, $R$",
            "conformance suite,\nJSON Schemas",
            "PCSF Studio,\npyCSAMT",
            "independent readers\n(h5py, h5dump)"]
    cys = [rows[0] - 1.0 - k * 13.0 for k in range(4)]
    # the encodings feed a bus that serves every consumer
    ax.plot([142.0, 146.0], [mid, mid], color=EDGE, lw=0.6)
    ax.plot([146.0, 146.0], [cys[-1], cys[0]], color=EDGE, lw=0.6)
    for yc, c in zip(cys, cons):
        box(ax, 150, yc - 5, 29, 10, c, NEU)
        arrow(ax, (146.0, yc), (149.4, yc))


def schematics():
    fig = plt.figure(figsize=(W_MM * fs.MM, H_MM * fs.MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_MM)
    ax.set_ylim(0, H_MM)
    ax.axis("off")
    data_chain(ax, H_MM - 4.0)
    data_model(ax, H_MM - 42.0)
    architecture(ax, H_MM - 108.0)
    fs.save(fig, "schematics")


if __name__ == "__main__":
    fs.apply()
    schematics()
    print("schematic written to", fs.FIG)
