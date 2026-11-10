"""Schematic figures for the PCSF Geophysics manuscript.

Produces, in ../Fig (PNG at 600 dpi and vector PDF):
  datachain     EM/MT data chain and the position of PCSF
  datamodel     logical PCSF data model and its two encodings
  architecture  reference implementation: adapters, model, encodings, consumers
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

import figstyle as fs

STD = "#dbe7f3"    # existing community standard
GAP = "#f8dcc8"    # PCSF
NEU = "#f0f0f0"
EDGE = "#4a4a4a"


def box(ax, x, y, w, h, text, fc, fs_=7, bold=False, ec=EDGE, lw=0.7, ha="center"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06",
                                fc=fc, ec=ec, lw=lw))
    tx = x + w / 2 if ha == "center" else x + 0.08
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs_,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def arrow(ax, p0, p1, both=False, color=EDGE):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="<|-|>" if both else "-|>",
                                 mutation_scale=6, lw=0.7, color=color,
                                 shrinkA=0, shrinkB=0))


def canvas(w_mm, h_mm, xmax, ymax):
    fig = plt.figure(figsize=(w_mm * fs.MM, h_mm * fs.MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax)
    ax.axis("off")
    return fig, ax


def datachain():
    fig, ax = canvas(183, 40, 18.3, 4.0)
    stages = [("Time series", "MTH5", STD), ("Transfer functions", "EDI, EMTF XML", STD),
              ("Inversion", "Occam2D, ModEM,\nMARE2DEM, ML", NEU),
              ("Resistivity model", "PCSF, PCSM\n(this paper)", GAP),
              ("Interpretation, reuse", "viewers, comparison,\narchives", NEU)]
    w, gap, x = 3.0, 0.75, 0.2
    for i, (name, std, fc) in enumerate(stages):
        box(ax, x, 2.1, w, 1.2, name, fc, fs_=7.5, bold=True)
        ax.text(x + w / 2, 1.85, std, ha="center", va="top", fontsize=6.5, color=fs.GREY)
        if i < len(stages) - 1:
            arrow(ax, (x + w + 0.08, 2.7), (x + w + gap - 0.08, 2.7))
        x += w + gap
    ax.add_patch(plt.Rectangle((0.2, 0.15), 0.35, 0.25, fc=STD, ec=EDGE, lw=0.5))
    ax.text(0.65, 0.275, "community exchange standard", va="center", fontsize=6.5)
    ax.add_patch(plt.Rectangle((4.6, 0.15), 0.35, 0.25, fc=GAP, ec=EDGE, lw=0.5))
    ax.text(5.05, 0.275, "representation introduced here", va="center", fontsize=6.5)
    fs.save(fig, "datachain")


def datamodel():
    fig, ax = canvas(183, 82, 18.3, 8.2)
    box(ax, 6.15, 6.6, 6.0, 1.2, "PCSF model\nversion, producing code, unit (ohm m), CRS",
        STD, fs_=7, bold=False)
    kids = [
        ("Geometry", "kind $\\kappa$: $\\mathsf{G}_2$, $\\mathsf{G}_3$,\n"
         "$\\mathsf{T}$ or $\\mathsf{L}$\ncells, nodes, coordinates"),
        ("Model", "resistivity (linear)\nnative values + encoding\nuncertainty, sensitivity"),
        ("Stations", "name, x, y, z\nline id\nlongitude, latitude"),
        ("Topography", "per station\nor raster"),
        ("Metadata", "survey, history,\nmodel record\n(learned predictors)"),
    ]
    w, gap = 3.3, 0.25
    x = 0.2
    for name, body in kids:
        ax.add_patch(FancyBboxPatch((x, 2.9), w, 2.7, boxstyle="round,pad=0,rounding_size=0.06",
                                    fc=NEU, ec=EDGE, lw=0.7))
        ax.text(x + w / 2, 5.3, name, ha="center", va="center", fontsize=7, fontweight="bold")
        ax.text(x + w / 2, 4.15, body, ha="center", va="center", fontsize=6.3,
                linespacing=1.3)
        arrow(ax, (9.15, 6.6), (x + w / 2, 5.62))
        x += w + gap
    ax.plot([0.2, 18.1], [2.45, 2.45], ls=(0, (3, 2)), color=fs.GREY, lw=0.5)
    ax.text(0.2, 2.2, "one in-memory model, two encodings", fontsize=6.3, color=fs.GREY,
            va="top")
    box(ax, 2.6, 0.25, 5.2, 1.3, "PCSF\nHDF5, binary, compressed", GAP, fs_=7)
    box(ax, 10.5, 0.25, 5.2, 1.3, "PCSM\nplain text, comments allowed", GAP, fs_=7)
    arrow(ax, (7.85, 0.9), (10.45, 0.9), both=True)
    ax.text(9.15, 1.05, "bit-exact", ha="center", va="bottom", fontsize=6.3)
    fs.save(fig, "datamodel")


def architecture():
    fig, ax = canvas(183, 78, 18.3, 7.8)
    srcs = ["Occam2D", "ModEM 3-D", "MARE2DEM", "EMC netCDF",
            "Learned predictor,\nother codes"]
    adps = ["occam2d_to_pcsf", "modem_to_pcsf", "mare2dem_to_pcsf",
            "emc_to_pcsf", "PCSFModel(...),\nplugin adapters"]
    ys = [6.3, 4.95, 3.6, 2.25, 0.9]
    ax.text(1.35, 7.55, "Solver output", ha="center", fontsize=7, fontweight="bold")
    ax.text(4.75, 7.55, "Adapters", ha="center", fontsize=7, fontweight="bold")
    ax.text(9.15, 7.55, "Common model", ha="center", fontsize=7, fontweight="bold")
    ax.text(15.5, 7.55, "Consumers", ha="center", fontsize=7, fontweight="bold")
    for y, s, a in zip(ys, srcs, adps):
        box(ax, 0.2, y, 2.3, 0.95, s, NEU, fs_=6.5)
        box(ax, 3.3, y, 2.9, 0.95, a, STD, fs_=6.2)
        ax.texts[-1].set_family("monospace")
        arrow(ax, (2.55, y + 0.475), (3.25, y + 0.475))
        arrow(ax, (6.25, y + 0.475), (7.15, 4.1))
    box(ax, 7.2, 2.1, 3.9, 4.0,
        "PCSFModel\n\ncanonicalise (eq. 1)\nproject nodes (eq. 2)\nvalidate shapes\n"
        "declare kind\nkeep provenance", GAP, fs_=6.5)
    ax.texts[-1].set_fontweight("normal")
    box(ax, 11.9, 4.6, 2.0, 1.0, ".pcsf\n(HDF5)", GAP, fs_=6.5)
    box(ax, 11.9, 2.6, 2.0, 1.0, ".pcsm\n(text)", GAP, fs_=6.5)
    arrow(ax, (11.15, 5.1), (11.85, 5.1), both=True)
    arrow(ax, (11.15, 3.1), (11.85, 3.1), both=True)
    arrow(ax, (12.9, 4.55), (12.9, 3.65), both=True)
    cons = ["sample_log10, compare_log10", "conformance suite,\nJSON Schemas",
            "PCSF Studio, pyCSAMT", "independent readers\n(h5py, h5dump)"]
    for i, c in enumerate(cons):
        y = 6.0 - i * 1.35
        box(ax, 14.6, y, 3.5, 0.95, c, NEU, fs_=6.2)
        arrow(ax, (13.95, 4.1), (14.55, y + 0.475))
    fs.save(fig, "architecture")


if __name__ == "__main__":
    fs.apply()
    datachain()
    datamodel()
    architecture()
    print("schematics written to", fs.FIG)
