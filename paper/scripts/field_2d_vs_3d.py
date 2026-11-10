"""Field example: 2-D (Occam2D) versus 3-D (ModEM) inversions of the
Baohuashan AMT survey, compared through PCSF files only.

Steps (Algorithm 2 of the manuscript):

1. Read the five Occam2D grid2d files and the ModEM grid3d file.
2. Register frames. Station longitudes/latitudes (WGS84) are projected
   to UTM zone 50N (EPSG:32650). The ModEM station table gives the same
   stations in the grid frame (station x/y minus the grid origin; x is
   northing, y is easting, as in ModEM). A least-squares affine map from
   UTM to the grid frame is fitted to the ModEM stations; its RMS
   residual is reported.
3. Target points. Along each line, points every DX m between the first
   and last station, at depths d = 0..D_MAX below the ground surface.
   Their longitude/latitude are interpolated along the Occam2D station
   chainage; the depth of the ground surface in the ModEM frame is
   interpolated from the ModEM station depths matched by station name.
4. Sample log10(rho) of both models with pcsf.algorithms.sample_log10
   and compare with pcsf.algorithms.compare_log10.

Outputs
  results/field_2d3d_by_line.csv, results/field_2d3d_by_depth.csv,
  results/field_2d3d_registration.json
  Fig/field_2d3d_sections.{png,pdf}, Fig/field_2d3d_slices.{png,pdf}
"""

from __future__ import annotations

import csv
import json
import warnings

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize, TwoSlopeNorm
from pyproj import Transformer
from scipy.interpolate import griddata

import figstyle as fs
import paths
from pcsf import get_inversion_record, read_pcsf
from pcsf.algorithms import compare_log10, sample_log10

warnings.filterwarnings("ignore")

LINES = ["L18", "L22", "L26", "L30", "L34"]
DX = 20.0           # m, along-line sampling
DZ = 10.0           # m, depth sampling
D_MAX = 1500.0      # m, maximum depth compared
AIR_RHO = 1e8       # ohm m; ModEM cells above this are air (topography)
D_LIM = 2.0         # colour limit of the difference maps (decades)
RUN_SUMMARY = paths.TABLES / "occam2d_run_summary.csv"
SLICE_DEPTHS = [100.0, 400.0, 1000.0]
DEPTH_BINS = [(0, 250), (250, 500), (500, 1000), (1000, 1500)]
TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32650", always_xy=True)


def key(n):
    return str(n)[:6]


# ------------------------------------------------------------ registration
def registration(m3):
    st = m3.stations
    e, n = TO_UTM.transform(st.lon, st.lat)
    ox, oy = m3.geometry.origin[:2]
    gx = st.x - ox        # grid frame, northing axis
    gy = st.y - oy        # grid frame, easting axis
    A = np.column_stack([e, n, np.ones_like(e)])
    cx, *_ = np.linalg.lstsq(A, gx, rcond=None)
    cy, *_ = np.linalg.lstsq(A, gy, rcond=None)
    res = np.hypot(A @ cx - gx, A @ cy - gy)
    info = {"n_stations": int(len(e)), "rms_residual_m": float(np.sqrt(np.mean(res ** 2))),
            "max_residual_m": float(res.max()), "coef_x": cx.tolist(), "coef_y": cy.tolist()}

    def to_grid(lon, lat):
        ee, nn = TO_UTM.transform(lon, lat)
        B = np.column_stack([ee, nn, np.ones_like(ee)])
        return B @ cx, B @ cy

    surf = {key(nm): z for nm, z in zip(st.name, st.z)}
    return to_grid, surf, info


# ------------------------------------------------------------ sampling
def line_samples(m2, m3, to_grid, surf3):
    st = m2.stations
    order = np.argsort(st.x)
    sx, slon, slat = st.x[order], st.lon[order], st.lat[order]
    snames = np.asarray(st.name)[order]
    zs3 = np.array([surf3.get(key(n), np.nan) for n in snames])
    ok = np.isfinite(zs3)
    xs = np.arange(sx[0], sx[-1] + 1e-6, DX)
    ds = np.arange(0.0, D_MAX + 1e-6, DZ)
    lon = np.interp(xs, sx, slon)
    lat = np.interp(xs, sx, slat)
    z0 = np.interp(xs, sx[ok], zs3[ok])
    gx, gy = to_grid(lon, lat)
    X, D = np.meshgrid(xs, ds)
    m2v = sample_log10(m2, np.column_stack([X.ravel(), D.ravel()])).reshape(D.shape)
    GX = np.broadcast_to(gx, X.shape)
    GY = np.broadcast_to(gy, X.shape)
    Z3 = np.broadcast_to(z0, X.shape) + D
    # grid3d points are (x, y, z) in the PCSF geometry order, where the
    # geometry x axis is ModEM's northing axis (= gx) and y is easting (= gy)
    m3v = sample_log10(m3, np.column_stack([GX.ravel(), GY.ravel(), Z3.ravel()])).reshape(D.shape)
    # Depth of investigation, read from the inversion record stored in the
    # Occam2D file, interpolated along the line.
    rec = get_inversion_record(m2)
    doi_map = rec.reliability["depth_of_investigation_m"]
    sdoi = np.array([doi_map.get(str(n), np.nan) for n in snames], float)
    okd = np.isfinite(sdoi)
    doi = np.interp(xs, sx[okd], sdoi[okd])
    # Ground elevation (m a.s.l.) from the station table of the Occam2D
    # file, for display in elevation; the comparison itself is made at
    # depth d below the ground.
    sz = np.asarray(st.z, float)[order]
    okz = np.isfinite(sz)
    elev = np.interp(xs, sx[okz], sz[okz])
    return {"x": xs, "d": ds, "m2": m2v, "m3": m3v, "lon": lon, "lat": lat,
            "sta_x": sx, "sta_z": sz, "elev": elev,
            "n_matched": int(ok.sum()), "n_sta": len(sx),
            "doi": doi, "inside": D <= doi[None, :]}


def slice_map(m3, to_grid, surf3_xy, depth, extent_ll, n=160):
    lon = np.linspace(extent_ll[0], extent_ll[1], n)
    lat = np.linspace(extent_ll[2], extent_ll[3], n)
    LON, LAT = np.meshgrid(lon, lat)
    gx, gy = to_grid(LON.ravel(), LAT.ravel())
    pts_xy, zs = surf3_xy
    z0 = griddata(pts_xy, zs, np.column_stack([gx, gy]), method="linear")
    z0n = griddata(pts_xy, zs, np.column_stack([gx, gy]), method="nearest")
    z0 = np.where(np.isfinite(z0), z0, z0n)
    v = sample_log10(m3, np.column_stack([gx, gy, z0 + depth]))
    e, nn = TO_UTM.transform(LON, LAT)
    return e, nn, v.reshape(LON.shape)


# ------------------------------------------------------------ main
def main():
    m3 = read_pcsf(fs.DATA / "baohuashan_modem3d.pcsf")
    # Air cells above the topography carry ~1e11 ohm m. Each takes the
    # value of the first earth cell below it, so that interpolation just
    # below the surface uses earth values only (ambiguity A5).
    rho = np.asarray(m3.resistivity, float).copy()
    air = rho > AIR_RHO
    n_air = int(air.sum())
    first = np.argmax(~air, axis=0)
    top = np.take_along_axis(rho, first[None], axis=0)[0]
    m3.resistivity = np.where(air, top[None], rho)
    print(f"air cells replaced: {n_air} of {rho.size}")
    runs = {}
    with RUN_SUMMARY.open() as fh:
        for r in csv.DictReader(fh):
            runs[r["line"]] = r
    m2s = {l: read_pcsf(fs.DATA / f"baohuashan_occam2d_{l}.pcsf") for l in LINES}
    to_grid, surf3, reg = registration(m3)
    print("registration:", {k: v for k, v in reg.items() if "coef" not in k})
    (fs.RESULTS / "field_2d3d_registration.json").write_text(json.dumps(reg, indent=2))

    samples = {l: line_samples(m2s[l], m3, to_grid, surf3) for l in LINES}

    def summary(m3v, m2v, inside):
        full = compare_log10(m3v, m2v).as_dict()
        a, b = np.where(inside, m3v, np.nan), np.where(inside, m2v, np.nan)
        doi = compare_log10(a, b).as_dict()
        f2 = m2v[inside & np.isfinite(m2v)]
        out = {k: round(v, 4) if isinstance(v, float) else v for k, v in full.items()}
        out.update({f"{k}_doi": round(v, 4) if isinstance(v, float) else v
                    for k, v in doi.items()})
        out["frac_2d_above_1e5_doi"] = round(float(np.mean(f2 > 5)), 4)
        out["frac_points_inside_doi"] = round(float(np.mean(inside)), 4)
        return out

    rows, all2, all3, alld, allin = [], [], [], [], []
    for l, s in samples.items():
        rows.append({"line": l, "stations": s["n_sta"], "matched": s["n_matched"],
                     "occam_rms": float(runs[l]["final_rms"]),
                     "occam_iterations": int(runs[l]["n_iterations"]),
                     "occam_converged": runs[l]["exit_code"] == "0",
                     "doi_min_m": round(float(s["doi"].min())),
                     "doi_median_m": round(float(np.median(s["doi"]))),
                     "frac_2d_above_1e5": round(float(np.mean(s["m2"][np.isfinite(s["m2"])] > 5)), 4),
                     **summary(s["m3"], s["m2"], s["inside"])})
        all2.append(s["m2"].ravel())
        all3.append(s["m3"].ravel())
        alld.append(np.broadcast_to(s["d"][:, None], s["m2"].shape).ravel())
        allin.append(s["inside"].ravel())
    a2, a3, ad, ain = map(np.concatenate, (all2, all3, alld, allin))
    rows.append({"line": "all", "stations": sum(x["stations"] for x in rows),
                 "matched": sum(x["matched"] for x in rows), "occam_rms": "",
                 "occam_iterations": "", "occam_converged": "",
                 "doi_min_m": min(x["doi_min_m"] for x in rows),
                 "doi_median_m": round(float(np.median(np.concatenate(
                     [samples[l]["doi"] for l in LINES])))),
                 "frac_2d_above_1e5": round(float(np.mean(a2[np.isfinite(a2)] > 5)), 4),
                 **summary(a3, a2, ain)})
    for row in rows:
        print(row)
    with (fs.RESULTS / "field_2d3d_by_line.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    drows = []
    for lo, hi in DEPTH_BINS:
        sel = (ad >= lo) & (ad < hi) if hi < D_MAX else (ad >= lo) & (ad <= hi)
        drows.append({"depth_min_m": lo, "depth_max_m": hi,
                      **summary(a3[sel], a2[sel], ain[sel])})
        print(drows[-1])
    with (fs.RESULTS / "field_2d3d_by_depth.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(drows[0]))
        w.writeheader()
        w.writerows(drows)

    vals = np.concatenate([a2[np.isfinite(a2)], a3[np.isfinite(a3)]])
    clim = (np.floor(np.percentile(vals, 2) * 2) / 2, np.ceil(np.percentile(vals, 98) * 2) / 2)
    fig_sections(samples, clim, rows)

    st = m3.stations
    ox, oy = m3.geometry.origin[:2]
    surf_xy = (np.column_stack([st.x - ox, st.y - oy]), st.z)
    pad = 0.0015
    ext = (min(s["lon"].min() for s in samples.values()) - pad,
           max(s["lon"].max() for s in samples.values()) + pad,
           min(s["lat"].min() for s in samples.values()) - pad,
           max(s["lat"].max() for s in samples.values()) + pad)
    slices = {d: slice_map(m3, to_grid, surf_xy, d, ext) for d in SLICE_DEPTHS}
    fig_slices(samples, slices, clim)


# ------------------------------------------------------------ figures
def fig_sections(samples, clim, rows):
    fs.apply()
    nl = len(LINES)
    fig = plt.figure(figsize=(fs.DOUBLE, 1.02 * fs.DOUBLE))
    gs = fig.add_gridspec(nl + 1, 3, height_ratios=[1] * nl + [0.07],
                          hspace=0.22, wspace=0.08)
    norm = Normalize(*clim)
    dnorm = TwoSlopeNorm(0.0, -D_LIM, D_LIM)
    stats = {r["line"]: r for r in rows}
    titles = ["Occam2D (2-D)", "ModEM (3-D), sampled along line",
              r"$\Delta = \log_{10}\rho_{3D} - \log_{10}\rho_{2D}$"]
    ims = [None, None, None]
    # Sections are drawn in elevation: a sample at depth d below the
    # ground at distance x lies at H(x) - d, with H the station
    # topography; the air above H is left blank.
    # The sampled window ends D_MAX below the ground, so its base
    # follows the topography; the axes stop at the shallowest base so
    # that every column is filled down to the lower edge.
    top = max(samples[l]["elev"].max() for l in LINES) / 1e3 + 0.08
    bottom = max(samples[l]["elev"].max() for l in LINES) / 1e3 - D_MAX / 1e3
    for i, l in enumerate(LINES):
        s = samples[l]
        xk = s["x"] / 1e3
        hk = s["elev"] / 1e3
        X, Dk = np.meshgrid(xk, s["d"] / 1e3)
        Y = hk[None, :] - Dk
        for j, (field, cmap, nrm) in enumerate(
                [(s["m2"], fs.RES_CMAP, norm), (s["m3"], fs.RES_CMAP, norm),
                 (s["m3"] - s["m2"], fs.DIFF_CMAP, dnorm)]):
            ax = fig.add_subplot(gs[i, j])
            ims[j] = ax.pcolormesh(X, Y, field, cmap=cmap, norm=nrm,
                                   shading="nearest", rasterized=True)
            # depth of investigation: dashed line, veil below it
            ydoi = hk - s["doi"] / 1e3
            ax.fill_between(xk, ydoi, hk - D_MAX / 1e3, color="white",
                            alpha=0.6, lw=0, zorder=3)
            ax.plot(xk, ydoi, ls=(0, (3, 1.5)), color=fs.INK, lw=0.6, zorder=4)
            ax.plot(xk, hk, color=fs.INK, lw=0.6, zorder=4)
            ax.set_ylim(bottom, top)
            ax.set_xlim(xk[0], xk[-1])
            ax.plot(s["sta_x"] / 1e3, s["sta_z"] / 1e3, "v", ms=2.2,
                    color=fs.INK, clip_on=False, zorder=5, mew=0)
            fs.boxed_spines(ax)
            if j == 0:
                ax.set_ylabel("Elevation (km)")
                ax.text(0.02, 0.05, l, transform=ax.transAxes, fontweight="bold",
                        fontsize=7, va="bottom",
                        bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.2))
            else:
                plt.setp(ax.get_yticklabels(), visible=False)
            if j == 2:
                st = stats[l]
                ax.text(0.98, 0.05,
                        rf"$\varepsilon$ = {st['rms_doi']:.2f}, $\beta$ = {st['bias_doi']:+.2f}, R = {st['correlation_doi']:.2f}",
                        transform=ax.transAxes, ha="right", va="bottom", fontsize=5.6,
                        bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.2))
            if i < nl - 1:
                plt.setp(ax.get_xticklabels(), visible=False)
            else:
                ax.set_xlabel("Distance along line (km)")
            if i == 0:
                ax.set_title(titles[j], loc="left", pad=3)
                fs.panel_label(ax, "abc"[j])
    for j in range(3):
        cax = fig.add_subplot(gs[nl, j])
        cax.set_position([cax.get_position().x0 + 0.02, cax.get_position().y0 - 0.025,
                          cax.get_position().width - 0.04, cax.get_position().height * 0.7])
        if j < 2:
            fs.log_rho_colorbar(fig, ims[j], cax, orientation="horizontal")
        else:
            cb = fig.colorbar(ims[2], cax=cax, orientation="horizontal",
                              ticks=[-2, -1, 0, 1, 2])
            cb.set_label(r"$\Delta$ (decades)")
            cb.outline.set_linewidth(0.5)
    fs.save(fig, "field_2d3d_sections")


def fig_slices(samples, slices, clim):
    fs.apply()
    nd = len(SLICE_DEPTHS)
    fig = plt.figure(figsize=(fs.DOUBLE, 0.50 * fs.DOUBLE))
    # pairs (rho, delta) per depth, with a spacer column between pairs
    ratios = []
    for j in range(nd):
        ratios += [1, 1] + ([0.28] if j < nd - 1 else [])
    gs = fig.add_gridspec(2, len(ratios), width_ratios=ratios,
                          height_ratios=[1, 0.035], wspace=0.06, hspace=0.16)
    norm = Normalize(*clim)
    dnorm = TwoSlopeNorm(0.0, -D_LIM, D_LIM)
    e0 = n0 = None
    col = 0
    first_ax = None
    for j, d in enumerate(SLICE_DEPTHS):
        E, N, V = slices[d]
        if e0 is None:
            e0, n0 = E.min(), N.min()
        k = int(round(d / DZ))
        for i in range(2):
            ax = fig.add_subplot(gs[0, col + i], sharey=first_ax)
            first_ax = first_ax or ax
            if i == 0:
                im = ax.pcolormesh((E - e0) / 1e3, (N - n0) / 1e3, V, cmap=fs.RES_CMAP,
                                   norm=norm, shading="nearest", rasterized=True)
            for l in LINES:
                s = samples[l]
                ee, nn = TO_UTM.transform(s["lon"], s["lat"])
                sub = slice(None, None, 5)          # one marker per 100 m
                xk, yk = (ee[sub] - e0) / 1e3, (nn[sub] - n0) / 1e3
                ins = s["inside"][k][sub]
                # points below the depth of investigation: open grey circles
                ax.scatter(xk[~ins], yk[~ins], s=6, facecolors="none", lw=0.4,
                           edgecolors=fs.GREY, zorder=4)
                if i == 0:
                    ax.scatter(xk[ins], yk[ins], c=s["m2"][k][sub][ins], cmap=fs.RES_CMAP,
                               norm=norm, s=6, lw=0.3, edgecolors=fs.INK, zorder=4)
                else:
                    ax.plot((ee - e0) / 1e3, (nn - n0) / 1e3, color=fs.LIGHT, lw=0.5,
                            zorder=2)
                    sd = ax.scatter(xk[ins], yk[ins], c=(s["m3"][k] - s["m2"][k])[sub][ins],
                                    cmap=fs.DIFF_CMAP, norm=dnorm, s=6, lw=0.3,
                                    edgecolors=fs.INK, zorder=4)
                if j == 0 and i == 0:
                    top = int(np.argmax(yk))
                    ax.text(xk[top], yk[top] + 0.06, l, fontsize=5.0, ha="center",
                            va="bottom")
            ax.set_xlim((E.min() - e0) / 1e3, (E.max() - e0) / 1e3)
            ax.set_ylim((N.min() - n0) / 1e3, (N.max() - n0) / 1e3 + 0.25)
            ax.set_aspect("equal")
            ax.set_xticks([0, 1])
            fs.boxed_spines(ax)
            ax.set_xlabel("E (km)", labelpad=1)
            if col + i == 0:
                ax.set_ylabel("Northing (km)")
            else:
                plt.setp(ax.get_yticklabels(), visible=False)
            ax.set_title(r"$\rho$" if i == 0 else r"$\Delta$", fontsize=6.5, pad=2)
        # depth label centred over the pair
        ax.text(-0.04, 1.075, f"{int(d)} m below surface", transform=ax.transAxes,
                ha="center", va="bottom", fontsize=7, fontweight="bold")
        col += 3
    cax = fig.add_subplot(gs[1, 0:5])
    fs.log_rho_colorbar(fig, im, cax, orientation="horizontal")
    cax = fig.add_subplot(gs[1, 6:])
    cb = fig.colorbar(sd, cax=cax, orientation="horizontal", ticks=[-2, -1, 0, 1, 2])
    cb.set_label(r"$\Delta = \log_{10}\rho_{3D} - \log_{10}\rho_{2D}$ (decades)")
    cb.outline.set_linewidth(0.5)
    fs.save(fig, "field_2d3d_slices")


if __name__ == "__main__":
    main()
