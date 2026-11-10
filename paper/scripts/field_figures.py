"""Field-example figures drawn from PCSF files only.

Fig/field_tongkeng.{png,pdf}     Occam2D grid2d section below station topography
Fig/field_mare2dem.{png,pdf}     MARE2DEM mesh_unstructured model, native mesh and
                                 point-location sampling (sample_log10)
Fig/field_baohuashan.{png,pdf}   multiline model: station map and fence view
"""

from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from pyproj import Transformer

import figstyle as fs
from pcsf import read_pcsf
from pcsf.algorithms import sample_log10

warnings.filterwarnings("ignore")
AIR = 1e8


def tongkeng():
    m = read_pcsf(fs.DATA / "tongkeng_occam2d.pcsf")
    g, st = m.geometry, m.stations
    sx, sz = np.asarray(st.x, float), np.asarray(st.z, float)
    lo, hi = sx.min() - 100, sx.max() + 100
    xn = np.clip(np.asarray(g.x_nodes, float), lo, hi)
    keep = np.where((g.x_nodes[1:] > lo) & (g.x_nodes[:-1] < hi))[0]
    xn = xn[keep[0]: keep[-1] + 2]
    zmax = 1500.0
    zn = np.asarray(g.z_nodes, float)
    kz = int(np.searchsorted(zn, zmax)) + 1
    zn = zn[:kz]
    v = np.log10(np.asarray(m.resistivity, float))[: kz - 1, keep[0]: keep[-1] + 1]
    elev_n = np.interp(xn, sx, sz)
    X = np.broadcast_to(xn, (zn.size, xn.size)) / 1e3
    Z = (elev_n[None, :] - zn[:, None]) / 1e3

    fs.apply()
    fig, ax = plt.subplots(figsize=(fs.DOUBLE, 0.45 * fs.DOUBLE))
    vals = v[np.isfinite(v)]
    norm = Normalize(np.floor(np.percentile(vals, 1)), np.ceil(np.percentile(vals, 99)))
    im = ax.pcolormesh(X, Z, v, cmap=fs.RES_CMAP, norm=norm, shading="flat",
                       rasterized=True)
    ax.plot(sx / 1e3, sz / 1e3, color=fs.INK, lw=0.6)
    ax.plot(sx / 1e3, sz / 1e3 + 0.012, "v", ms=2.6, color=fs.INK, mew=0,
            clip_on=False)
    for i in range(0, len(sx), 5):
        ax.text(sx[i] / 1e3, sz[i] / 1e3 + 0.04, st.name[i], ha="center",
                va="bottom", fontsize=5.4, rotation=90)
    ax.set_xlim(lo / 1e3, hi / 1e3)
    ax.set_ylim(-0.6, sz.max() / 1e3 + 0.25)
    ax.set_aspect("equal")
    ax.set_xlabel("Distance along profile (km)")
    ax.set_ylabel("Elevation (km)")
    fs.boxed_spines(ax)
    cax = ax.inset_axes([1.015, 0.0, 0.012, 0.8])
    fs.log_rho_colorbar(fig, im, cax)
    fs.save(fig, "field_tongkeng")


def mare2dem():
    m = read_pcsf(fs.DATA / "mare2dem_demo.pcsf")
    g = m.geometry
    P = np.asarray(g.nodes, float)[np.asarray(g.connectivity)]
    r = np.asarray(m.resistivity, float)
    logr = np.where(r > AIR, np.nan, np.log10(r))
    norm = Normalize(-0.5, 2.0)
    cmap = fs.RES_CMAP.copy()
    cmap.set_bad("#eef2f6")
    c = P.mean(axis=1) / 1e3

    fs.apply()
    fig = plt.figure(figsize=(fs.DOUBLE, 0.62 * fs.DOUBLE))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.62], hspace=0.38, wspace=0.08)
    zoom = (6.0, 14.0, 4.0, 1.4)   # x0, x1, z_bottom, z_top (km)

    ax = fig.add_subplot(gs[0, :])
    sel = (c[:, 0] > -10) & (c[:, 0] < 40) & (c[:, 1] < 20)
    pc = PolyCollection(P[sel] / 1e3, array=logr[sel], cmap=cmap, norm=norm,
                        edgecolors="face", linewidths=0.05)
    ax.add_collection(pc)
    ax.add_patch(plt.Rectangle((zoom[0], zoom[3]), zoom[1] - zoom[0], zoom[2] - zoom[3],
                               fill=False, ec=fs.INK, lw=0.7, ls="--"))
    ax.set_xlim(-4, 30)
    ax.set_ylim(14, 0)
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Depth (km)")
    ax.set_title(f"Native mesh: {len(r)} triangles, "
                 f"{len(np.asarray(m.resistivity_by_region))} regions "
                 "(air not shown)", loc="left", pad=3)
    fs.boxed_spines(ax)
    fs.panel_label(ax, "a")
    cax = ax.inset_axes([1.01, 0.0, 0.012, 1.0])
    fs.log_rho_colorbar(fig, pc, cax)

    ax = fig.add_subplot(gs[1, 0])
    sel = ((c[:, 0] > zoom[0] - 2) & (c[:, 0] < zoom[1] + 2) & (c[:, 1] < zoom[2] + 2))
    pc = PolyCollection(P[sel] / 1e3, array=logr[sel], cmap=cmap, norm=norm,
                        edgecolors="white", linewidths=0.2)
    ax.add_collection(pc)
    ax.set_title("Detail, native triangles", loc="left", pad=3)
    axes = [ax]

    ax = fig.add_subplot(gs[1, 1], sharey=axes[0])
    xs = np.linspace(zoom[0], zoom[1], 400) * 1e3
    zs = np.linspace(zoom[3], zoom[2], 130) * 1e3
    Xg, Zg = np.meshgrid(xs, zs)
    v = sample_log10(m, np.column_stack([Xg.ravel(), Zg.ravel()])).reshape(Xg.shape)
    v = np.where(v > np.log10(AIR), np.nan, v)
    ax.pcolormesh(xs / 1e3, zs / 1e3, v, cmap=cmap, norm=norm, shading="nearest",
                  rasterized=True)
    ax.set_title("Same window sampled by point location (20 m grid)", loc="left", pad=3)
    plt.setp(ax.get_yticklabels(), visible=False)
    axes.append(ax)
    for a, letter in zip(axes, "bc"):
        a.set_xlim(zoom[0], zoom[1])
        a.set_ylim(zoom[2], zoom[3])
        a.set_xlabel("Distance (km)")
        fs.boxed_spines(a)
        fs.panel_label(a, letter)
    axes[0].set_ylabel("Depth (km)")
    fs.save(fig, "field_mare2dem")


def baohuashan():
    from pcsf import PCSFModel

    ml = read_pcsf(fs.DATA / "baohuashan_multiline.pcsf")
    lines = ml.geometry.lines
    st = ml.stations
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32650", always_xy=True)
    E, N = to_utm.transform(st.lon, st.lat)
    e0, n0 = np.nanmin(E), np.nanmin(N)
    lid = np.asarray(st.line_id)

    fs.apply()
    fig = plt.figure(figsize=(fs.DOUBLE, 0.46 * fs.DOUBLE))
    ax = fig.add_axes([0.06, 0.12, 0.17, 0.80])
    colors = [fs.C_BLUE, fs.C_ORANGE, fs.C_GREEN, fs.C_RED, fs.C_PURPLE]
    for c, line in zip(colors, lines):
        s = lid == line.line_id
        ax.plot((E[s] - e0) / 1e3, (N[s] - n0) / 1e3, "o-", ms=2.0, lw=0.6, color=c,
                mew=0)
        top = np.argmax(N[s])
        ax.text((E[s][top] - e0) / 1e3, (N[s][top] - n0) / 1e3 + 0.07,
                line.line_id[1:], ha="center", va="bottom", fontsize=5.8, color=c)
    ax.set_aspect("equal")
    ax.set_xlim(-0.15, 1.0)
    ax.set_ylim(-0.1, 3.0)
    ax.set_xlabel("Easting (km)")
    ax.set_ylabel("Northing (km)")
    fs.boxed_spines(ax)
    fs.panel_label(ax, "a")
    ax.set_title("Lines (UTM 50N)", loc="left", pad=3)

    ax3 = fig.add_axes([0.25, 0.0, 0.66, 1.0], projection="3d")
    norm = Normalize(2.0, 6.0)
    zmax = 1500.0
    for line in lines:
        s = lid == line.line_id
        sx = np.asarray(st.x)[s]
        xs = np.linspace(sx.min(), sx.max(), 120)
        zs = np.linspace(0, zmax, 60)
        Xg, Zg = np.meshgrid(xs, zs)
        sub = PCSFModel(geometry=line.geometry, resistivity=line.resistivity)
        v = sample_log10(sub, np.column_stack([Xg.ravel(), Zg.ravel()])).reshape(Xg.shape)
        Y = np.full_like(Xg, line.offset_y)
        ax3.plot_surface(Xg / 1e3, Y / 1e3, -Zg / 1e3, facecolors=fs.RES_CMAP(norm(v)),
                         rstride=1, cstride=1, linewidth=0, antialiased=False, shade=False)
        ax3.text(sx.min() / 1e3 - 0.05, line.offset_y / 1e3, 0.08, line.line_id,
                 fontsize=6)
    ax3.set_xlabel("Distance along line (km)", labelpad=-2)
    ax3.set_ylabel("Offset (km)", labelpad=-2)
    ax3.set_zlabel("Depth (km)", labelpad=-4)
    ax3.view_init(elev=22, azim=-60)
    ax3.set_box_aspect((2.4, 1.0, 1.0))
    ax3.tick_params(pad=-1, labelsize=5.8)
    ax3.set_yticks([0.0, 0.4, 0.8])
    ax3.set_zticks([0, -0.5, -1.0, -1.5])
    ax3.set_zticklabels(["0", "0.5", "1.0", "1.5"])
    for a in (ax3.xaxis, ax3.yaxis, ax3.zaxis):
        a.pane.set_facecolor((1, 1, 1, 0))
        a.pane.set_edgecolor(fs.LIGHT)
    fig.text(0.29, 0.93, "b", fontsize=8, fontweight="bold")
    fig.text(0.31, 0.93, "Fence view of the multiline file, lines at measured offsets",
             fontsize=7)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=fs.RES_CMAP)
    cax = fig.add_axes([0.93, 0.22, 0.012, 0.56])
    fs.log_rho_colorbar(fig, sm, cax)
    fs.save(fig, "field_baohuashan")


if __name__ == "__main__":
    tongkeng()
    mare2dem()
    baohuashan()
