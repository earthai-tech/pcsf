"""Test 2: accuracy of node-to-cell projection, mesh sampling and grid
resampling on a synthetic resistivity model with a known exact field.

The exact field m*(x, z) = log10 rho*(x, z) (x in [0, 4000] m, depth
z in [0, 2000] m) has

* a two-layer background: 100 ohm m above, 1000 ohm m below a
  transition at 400 m depth (tanh, half-width 60 m);
* a dipping conductor: 1.5 decades lower along a plane through
  (1500 m, 300 m) dipping 35 degrees, Gaussian half-width 120 m,
  tapered between 250 m and 1400 m depth;
* a resistive block: +0.8 decade over x in [2800, 3400] m,
  z in [200, 700] m, with 40 m smooth edges.

For each characteristic cell size h, the test measures the RMS error
eps (in log10 ohm m) on a 5 m evaluation grid of

  M1  mesh, cell value = exact value at centroid, point-location sampling
      (the discretization floor of a piecewise-constant mesh model);
  M2  mesh, cell value = arithmetic mean of linear rho at the 3 nodes
      (node-to-cell projection, arithmetic);
  M3  mesh, cell value = mean of log10 rho at the 3 nodes
      (node-to-cell projection, geometric);
  G1  grid, cell-centre values, linear interpolation in log10 rho;
  G2  grid, cell-centre values, linear interpolation in rho;
  G3  grid, cell-centre values, nearest cell.

M1-M3 use the reference implementation (pcsf: node_to_cell and
pcsf.algorithms.sample_log10); G1 uses sample_log10;
G2 and G3 are the alternatives it is compared against.

Outputs: results/test2_sampling_accuracy.csv, Fig/test2_sampling.{png,pdf}
"""

from __future__ import annotations

import csv

import matplotlib.pyplot as plt
import numpy as np
import triangle as tr
from matplotlib.collections import PolyCollection
from scipy.interpolate import RegularGridInterpolator

import figstyle as fs
from pcsf import Grid2DGeometry, PCSFModel, UnstructuredMeshGeometry
from pcsf.algorithms import node_to_cell, sample_log10

XMAX, ZMAX = 4000.0, 2000.0
EVAL_DX = 5.0
SIZES = [400.0, 200.0, 100.0, 50.0, 25.0]


def mesh_to_pcsf(nodes, tri, resistivity=None, resistivity_by_node=None):
    """Mesh model with per-cell resistivity; per-node values are
    projected with the arithmetic mean (pyCSAMT's default)."""
    if resistivity is None:
        resistivity = node_to_cell(tri, resistivity_by_node, "arithmetic")
    geo = UnstructuredMeshGeometry(nodes=nodes, connectivity=tri,
                                   region_ids=np.zeros(len(tri), int))
    return PCSFModel(geometry=geo, resistivity=resistivity,
                     resistivity_by_node=resistivity_by_node)


def exact(x, z):
    """Exact log10 resistivity m*(x, z)."""
    x = np.asarray(x, float)
    z = np.asarray(z, float)
    m = 2.0 + 0.5 * (1.0 + np.tanh((z - 400.0) / 60.0))
    dip = np.deg2rad(35.0)
    # signed distance to the dipping plane through (1500, 300)
    d = (x - 1500.0) * np.sin(dip) - (z - 300.0) * np.cos(dip)
    taper = 0.25 * (1 + np.tanh((z - 250.0) / 40.0)) * (1 + np.tanh((1400.0 - z) / 80.0))
    m = m - 1.5 * np.exp(-0.5 * (d / 120.0) ** 2) * taper
    bx = 0.25 * (1 + np.tanh((x - 2800.0) / 40.0)) * (1 + np.tanh((3400.0 - x) / 40.0))
    bz = 0.25 * (1 + np.tanh((z - 200.0) / 40.0)) * (1 + np.tanh((700.0 - z) / 40.0))
    return m + 0.8 * bx * bz


def eval_grid():
    xe = np.arange(0.0, XMAX + 1e-9, EVAL_DX)
    ze = np.arange(0.0, ZMAX + 1e-9, EVAL_DX)
    X, Z = np.meshgrid(xe, ze)
    return xe, ze, X, Z


def quality_mesh(h):
    """Unstructured quality triangulation with characteristic size h."""
    pts = np.array([[0, 0], [XMAX, 0], [XMAX, ZMAX], [0, ZMAX]], float)
    segs = np.array([[0, 1], [1, 2], [2, 3], [3, 0]])
    area = np.sqrt(3) / 4 * h * h
    t = tr.triangulate({"vertices": pts, "segments": segs}, f"pq30a{area:.3f}")
    return t["vertices"], t["triangles"]


def rms(a, b):
    d = a - b
    d = d[np.isfinite(d)]
    return float(np.sqrt(np.mean(d * d)))


def run():
    xe, ze, X, Z = eval_grid()
    truth = exact(X, Z)
    pts = np.column_stack([X.ravel(), Z.ravel()])
    rows = []
    meshes = {}
    for h in SIZES:
        nodes, tri = quality_mesh(h)
        cent = nodes[tri].mean(axis=1)
        node_lin = 10.0 ** exact(nodes[:, 0], nodes[:, 1])

        # M1: exact centroid value
        m1 = mesh_to_pcsf(nodes, tri, resistivity=10.0 ** exact(cent[:, 0], cent[:, 1]))
        # M2: node values -> arithmetic mean of linear rho (library default)
        m2 = mesh_to_pcsf(nodes, tri, resistivity_by_node=node_lin)
        # M3: node values -> mean of log10 rho
        m3 = mesh_to_pcsf(nodes, tri,
                          resistivity=10.0 ** np.log10(node_lin)[tri].mean(axis=1))
        e = {}
        for key, model in (("M1", m1), ("M2", m2), ("M3", m3)):
            e[key] = rms(sample_log10(model, pts), truth.ravel())

        # Grid with cell size h, cell-centre values.
        xc = np.arange(h / 2, XMAX, h)
        zc = np.arange(h / 2, ZMAX, h)
        Xc, Zc = np.meshgrid(xc, zc)
        g_log = exact(Xc, Zc)
        grid = PCSFModel(
            geometry=Grid2DGeometry(x=xc, z=zc,
                                    x_nodes=np.arange(0, XMAX + 1e-9, h),
                                    z_nodes=np.arange(0, ZMAX + 1e-9, h)),
            resistivity=10.0 ** g_log,
        )
        e["G1"] = rms(sample_log10(grid, pts), truth.ravel())
        q = np.column_stack([np.clip(Z.ravel(), zc[0], zc[-1]),
                             np.clip(X.ravel(), xc[0], xc[-1])])
        lin = RegularGridInterpolator((zc, xc), 10.0 ** g_log)(q)
        e["G2"] = rms(np.log10(lin), truth.ravel())
        near = RegularGridInterpolator((zc, xc), g_log, method="nearest")(q)
        e["G3"] = rms(near, truth.ravel())

        rows.append({"h_m": h, "n_triangles": int(tri.shape[0]),
                     "n_grid_cells": int(xc.size * zc.size), **e})
        meshes[h] = (nodes, tri)
        print(f"h={h:6.1f}  tri={tri.shape[0]:7d}  " +
              "  ".join(f"{k}={v:.4f}" for k, v in e.items()))

    out = fs.RESULTS / "test2_sampling_accuracy.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # Convergence orders from a least-squares fit in log-log space.
    hs = np.array([r["h_m"] for r in rows])
    orders = {}
    for k in ("M1", "M2", "M3", "G1", "G2", "G3"):
        ev = np.array([r[k] for r in rows])
        orders[k] = float(np.polyfit(np.log(hs), np.log(ev), 1)[0])
    with (fs.RESULTS / "test2_orders.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["method", "order"])
        for k, v in orders.items():
            w.writerow([k, f"{v:.3f}"])
    print("orders:", {k: round(v, 2) for k, v in orders.items()})
    figure(xe, ze, truth, meshes[200.0], rows, orders)


def figure(xe, ze, truth, mesh200, rows, orders):
    fs.apply()
    fig = plt.figure(figsize=(fs.DOUBLE, 0.40 * fs.DOUBLE))
    gs = fig.add_gridspec(2, 4, width_ratios=[1.0, 0.035, 0.48, 0.95],
                          height_ratios=[1, 1], hspace=0.38, wspace=0.05)
    vmin, vmax = 1.0, 3.5

    # (a) exact field
    ax = fig.add_subplot(gs[0, 0])
    im = ax.imshow(truth, extent=[0, XMAX / 1e3, ZMAX / 1e3, 0], cmap=fs.RES_CMAP,
                   vmin=vmin, vmax=vmax, aspect="equal", interpolation="none")
    ax.set_ylabel("Depth (km)")
    plt.setp(ax.get_xticklabels(), visible=False)
    fs.boxed_spines(ax)
    fs.panel_label(ax, "a")
    ax.set_title("Exact model", loc="left", pad=2)

    # (b) mesh h = 200 m, cells from the log10 node mean
    axb = fig.add_subplot(gs[1, 0], sharex=ax)
    nodes, tri = mesh200
    node_log = exact(nodes[:, 0], nodes[:, 1])
    cell = node_log[tri].mean(axis=1)
    pc = PolyCollection(nodes[tri] / 1e3, array=cell, cmap=fs.RES_CMAP,
                        edgecolors="white", linewidths=0.12)
    pc.set_clim(vmin, vmax)
    axb.add_collection(pc)
    axb.set_xlim(0, XMAX / 1e3)
    axb.set_ylim(ZMAX / 1e3, 0)
    axb.set_aspect("equal")
    axb.set_xlabel("Distance (km)")
    axb.set_ylabel("Depth (km)")
    fs.boxed_spines(axb)
    fs.panel_label(axb, "b")
    axb.set_title(f"Mesh, h = 200 m ({tri.shape[0]} triangles)",
                  loc="left", pad=2)

    cax = fig.add_subplot(gs[:, 1])
    fs.log_rho_colorbar(fig, im, cax)

    # (c) convergence
    axc = fig.add_subplot(gs[:, 3])
    hs = np.array([r["h_m"] for r in rows])
    styles = {
        "M1": (fs.C_BLACK, "o", "-", "Mesh, exact cell value"),
        "M2": (fs.C_RED, "s", "-", r"Mesh, node mean of $\rho$"),
        "M3": (fs.C_BLUE, "^", "-", r"Mesh, node mean of $\log_{10}\rho$"),
        "G1": (fs.C_GREEN, "o", "--", r"Grid, linear in $\log_{10}\rho$"),
        "G2": (fs.C_ORANGE, "s", "--", r"Grid, linear in $\rho$"),
        "G3": (fs.C_PURPLE, "D", ":", "Grid, nearest cell"),
    }
    for k, (c, mk, ls, lab) in styles.items():
        ev = np.array([r[k] for r in rows])
        axc.loglog(hs, ev, ls=ls, marker=mk, ms=3, color=c, lw=0.9, mew=0,
                   label=f"{lab} ({orders[k]:.2f})")
    # slope triangles (order 1 and 2) in the empty upper-left corner
    for (h0, y0, p, lab) in ((25.0, 0.10, 1, "1"), (25.0, 0.30, 2, "2")):
        h1 = 2.0 * h0
        y1 = y0 * 2.0 ** p
        axc.plot([h0, h1, h1, h0], [y0, y0, y1, y0], color=fs.GREY, lw=0.5)
        axc.text(h1 * 1.05, np.sqrt(y0 * y1), lab, color=fs.GREY, va="center",
                 fontsize=5.8)
    axc.text(25.0, 0.075, "slope", color=fs.GREY, fontsize=5.8, va="top")
    axc.set_xlim(18, 700)
    axc.set_xticks([25, 50, 100, 200, 400])
    axc.set_xticklabels(["25", "50", "100", "200", "400"])
    axc.minorticks_off()
    axc.set_ylim(2e-4, 3.0)
    axc.set_xlabel("Cell size h (m)")
    axc.set_ylabel(r"RMS error $\varepsilon$ ($\log_{10}$ $\Omega$ m)")
    axc.legend(loc="lower right", handlelength=2.4, fontsize=5.8,
               title="Method (fitted order)", title_fontsize=6)
    fs.panel_label(axc, "c")
    fs.save(fig, "test2_sampling")


if __name__ == "__main__":
    run()
