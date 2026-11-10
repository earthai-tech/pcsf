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
from matplotlib.colors import ListedColormap, Normalize
from pyproj import Transformer

import figstyle as fs
import paths
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


SEA = "#cfe4f2"   # fixed seawater regions, outside the resistivity scale


def mare2dem_fixed_sea(path):
    """Numbers of the fixed regions below 1 ohm m (seawater).

    In a MARE2DEM .resistivity file every region row gives its
    resistivity and a parameter number, 0 for a fixed region; the sea
    is fixed at its known resistivity (0.3 ohm m in the demonstration)
    and the air at 1e12 ohm m. Regions are numbered from 1, as in the
    file and in the region ids that the MARE2DEM adapter stores.
    """
    ids, on = [], False
    for ln in path.read_text().splitlines():
        if ln.strip().startswith("!#"):
            on = True
            continue
        if on and ln.strip():
            p = ln.split()
            if int(p[2]) == 0 and float(p[1]) < 1.0:
                ids.append(int(p[0]))
    return np.array(ids, dtype=int)


def mare2dem_receivers(path):
    """Horizontal position and depth (km) of the MT receivers."""
    lines = path.read_text().splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith("# MT Receivers"))
    n = int(lines[i].split(":")[1])
    rows = [ln.split() for ln in lines[i + 2:i + 2 + n]]
    return (np.array([float(r[1]) for r in rows]) / 1e3,
            np.array([float(r[2]) for r in rows]) / 1e3)


def interface_segments(conn, a, b):
    """Edges shared by a triangle of set a and a triangle of set b."""
    owner = {}
    for k, tri in enumerate(conn):
        for e in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            owner.setdefault(tuple(sorted(e)), []).append(k)
    return [e for e, ks in owner.items()
            if len(ks) == 2 and ((a[ks[0]] and b[ks[1]]) or (a[ks[1]] and b[ks[0]]))]


def mare2dem():
    from matplotlib.collections import LineCollection
    from pcsf.algorithms import locate_triangles

    m = read_pcsf(fs.DATA / "mare2dem_demo.pcsf")
    g = m.geometry
    nodes = np.asarray(g.nodes, float)
    conn = np.asarray(g.connectivity)
    P = nodes[conn]
    r = np.asarray(m.resistivity, float)
    sea = np.isin(np.asarray(g.region_ids), mare2dem_fixed_sea(
        paths.MARE2DEM / "demo.6.resistivity"))
    air = r > AIR
    earth = ~sea & ~air
    logr = np.log10(r)
    norm = Normalize(-0.5, 2.0)
    cmap = fs.RES_CMAP
    lo, hi = P.min(axis=1) / 1e3, P.max(axis=1) / 1e3
    floor = interface_segments(conn, sea, earth)
    floor_xy = [nodes[list(e)] / 1e3 for e in floor]
    rx, rz = mare2dem_receivers(paths.MARE2DEM / "demo_mt_synth_static.emdata")

    def window(x0, x1, z0, z1):
        # triangles overlapping the window (not by centroid: the long
        # thin triangles of the water layer reach far beyond it)
        return (lo[:, 0] <= x1) & (hi[:, 0] >= x0) & (lo[:, 1] <= z1) & (hi[:, 1] >= z0)

    def draw(ax, sel, edge, lw):
        ax.add_collection(PolyCollection(P[sel & sea] / 1e3, facecolors=SEA,
                                         edgecolors=SEA, linewidths=0.05))
        pc = PolyCollection(P[sel & earth] / 1e3, array=logr[sel & earth],
                            cmap=cmap, norm=norm, edgecolors=edge,
                            linewidths=lw)
        ax.add_collection(pc)
        ax.add_collection(LineCollection(floor_xy, colors=fs.INK, linewidths=0.6))
        ax.plot(rx, rz, "v", ms=3.0, color=fs.INK, mew=0, zorder=5, clip_on=True)
        return pc

    fs.apply()
    fig = plt.figure(figsize=(fs.DOUBLE, 0.62 * fs.DOUBLE))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.62], hspace=0.38, wspace=0.08)
    zoom = (6.0, 14.0, 4.0, 1.4)   # x0, x1, z_bottom, z_top (km)

    ax = fig.add_subplot(gs[0, :])
    pc = draw(ax, window(-4, 30, 0, 14), "face", 0.05)
    ax.add_patch(plt.Rectangle((zoom[0], zoom[3]), zoom[1] - zoom[0], zoom[2] - zoom[3],
                               fill=False, ec=fs.INK, lw=0.7, ls="--"))
    ax.text(28.5, 0.55, "sea water (0.3 $\\Omega$ m, fixed)", ha="right",
            va="center", fontsize=6, color=fs.INK)
    ax.set_xlim(-4, 30)
    ax.set_ylim(14, 0)
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Depth below sea level (km)")
    ax.set_title(f"Native mesh: {len(r)} triangles, "
                 f"{len(np.asarray(m.resistivity_by_region))} regions; "
                 f"{len(rx)} seafloor receivers", loc="left", pad=3)
    fs.boxed_spines(ax)
    fs.panel_label(ax, "a")
    cax = ax.inset_axes([1.01, 0.0, 0.012, 1.0])
    fs.log_rho_colorbar(fig, pc, cax)

    ax = fig.add_subplot(gs[1, 0])
    draw(ax, window(zoom[0], zoom[1], zoom[3], zoom[2]), "white", 0.2)
    ax.set_title("Detail, native triangles", loc="left", pad=3)
    axes = [ax]

    ax = fig.add_subplot(gs[1, 1], sharey=axes[0])
    xs = np.linspace(zoom[0], zoom[1], 400) * 1e3
    zs = np.linspace(zoom[3], zoom[2], 130) * 1e3
    Xg, Zg = np.meshgrid(xs, zs)
    pts = np.column_stack([Xg.ravel(), Zg.ravel()])
    v = sample_log10(m, pts).reshape(Xg.shape)
    tri = locate_triangles(nodes, conn, pts).reshape(Xg.shape)
    in_sea = (tri >= 0) & sea[np.clip(tri, 0, None)]
    in_air = (tri >= 0) & air[np.clip(tri, 0, None)]
    ax.pcolormesh(xs / 1e3, zs / 1e3, np.where(in_sea, 1.0, np.nan),
                  cmap=ListedColormap([SEA]), shading="nearest", rasterized=True)
    ax.pcolormesh(xs / 1e3, zs / 1e3, np.where(in_sea | in_air, np.nan, v),
                  cmap=cmap, norm=norm, shading="nearest", rasterized=True)
    ax.add_collection(LineCollection(floor_xy, colors=fs.INK, linewidths=0.6))
    ax.plot(rx, rz, "v", ms=3.0, color=fs.INK, mew=0, zorder=5)
    ax.set_title("Same window sampled by point location (20 m grid)", loc="left", pad=3)
    plt.setp(ax.get_yticklabels(), visible=False)
    axes.append(ax)
    for a, letter in zip(axes, "bc"):
        a.set_xlim(zoom[0], zoom[1])
        a.set_ylim(zoom[2], zoom[3])
        a.set_xlabel("Distance (km)")
        fs.boxed_spines(a)
        fs.panel_label(a, letter)
    axes[0].set_ylabel("Depth below sea level (km)")
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
    # Each panel is drawn in elevation: a sample at depth d below the
    # ground at distance x lies at H(x) - d, with H interpolated between
    # the station elevations; stations sit on the topographic line.
    for line in lines:
        s = lid == line.line_id
        sx = np.asarray(st.x)[s]
        sz = np.asarray(st.z, float)[s]
        order = np.argsort(sx)
        sx, sz = sx[order], sz[order]
        xs = np.linspace(sx.min(), sx.max(), 120)
        zs = np.linspace(0, zmax, 60)
        Xg, Zg = np.meshgrid(xs, zs)
        H = np.interp(xs, sx, sz)
        sub = PCSFModel(geometry=line.geometry, resistivity=line.resistivity)
        v = sample_log10(sub, np.column_stack([Xg.ravel(), Zg.ravel()])).reshape(Xg.shape)
        Y = np.full_like(Xg, line.offset_y)
        ax3.plot_surface(Xg / 1e3, Y / 1e3, (H[None, :] - Zg) / 1e3,
                         facecolors=fs.RES_CMAP(norm(v)), rstride=1, cstride=1,
                         linewidth=0, antialiased=False, shade=False)
        yl = np.full_like(xs, line.offset_y) / 1e3
        ax3.plot(xs / 1e3, yl, H / 1e3, color=fs.INK, lw=0.6, zorder=10)
        ax3.scatter(sx / 1e3, np.full_like(sx, line.offset_y) / 1e3, sz / 1e3,
                    marker="v", s=4, color=fs.INK, depthshade=False, lw=0)
        ax3.text(sx.min() / 1e3 - 0.05, line.offset_y / 1e3, H[0] / 1e3 + 0.12,
                 line.line_id, fontsize=6)
    ax3.set_xlabel("Distance along line (km)", labelpad=-2)
    ax3.set_ylabel("Offset (km)", labelpad=-2)
    ax3.set_zlabel("Elevation (km)", labelpad=-4)
    ax3.view_init(elev=22, azim=-60)
    ax3.set_box_aspect((2.4, 1.0, 1.0))
    ax3.tick_params(pad=-1, labelsize=5.8)
    ax3.set_yticks([0.0, 0.4, 0.8])
    ax3.set_zticks([0, -0.5, -1.0])
    for a in (ax3.xaxis, ax3.yaxis, ax3.zaxis):
        a.pane.set_facecolor((1, 1, 1, 0))
        a.pane.set_edgecolor(fs.LIGHT)
    fig.text(0.29, 0.93, "b", fontsize=8, fontweight="bold")
    fig.text(0.31, 0.93, "Fence view of the multiline file, lines at measured "
             "offsets, in elevation with stations",
             fontsize=7)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=fs.RES_CMAP)
    cax = fig.add_axes([0.93, 0.22, 0.012, 0.56])
    fs.log_rho_colorbar(fig, sm, cax)
    fs.save(fig, "field_baohuashan")


if __name__ == "__main__":
    tongkeng()
    mare2dem()
    baohuashan()
