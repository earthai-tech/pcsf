"""Round trip of community-archive models (IRIS/EarthScope Earth Model
Collaboration, EMC) through PCSF, and comparison of each archived netCDF
model with the ModEM solver file it was made from.

Models (downloaded from data.earthscope.org into data/emc_raw):
  MCR-MT-2016 (Bedrosian, 2016), THO-MT-2021 (Bedrosian and Finn, 2021),
  WUS-MT-2021 (Murphy et al., 2021). Each EMC product has a netCDF-4
  classic file (log10 conductivity on a 0.1 degree latitude/longitude grid)
  and the original ModEM .rho file with a readme stating the projection.

Part A, lossless round trip:
  EMC netCDF -> PCSF -> PCSM -> PCSF -> EMC netCDF, then compare with the
  original: data (raw values including fill values), coordinates, global
  and variable attributes (names, values and types), file format.
Part B, archive versus solver file:
  sample the ModEM model (via PCSF, pcsf.algorithms.sample_log10) at the EMC
  grid points, using the transverse Mercator projection of the readme, and
  compare with the archived values, for linear and nearest-cell sampling,
  for the readme false northing and for the centre stated in the readme.
Part C, inversion record of the EMC-derived PCSF files (what the archive
  metadata can fill).

Outputs: results/emc_roundtrip.csv, results/emc_vs_solver.csv,
         results/emc_records.csv, Fig/emc_vs_solver.{png,pdf}
"""

from __future__ import annotations

import csv
import json
import tempfile
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import netCDF4
import numpy as np
from matplotlib.colors import Normalize, TwoSlopeNorm
from pyproj import Transformer

import figstyle as fs
import paths
from pcsf import (Grid3DGeometry, InversionRecord,
                  attach_inversion_record, check_inversion_record,
                  read_pcsf, read_pcsm, write_pcsf, write_pcsm)
from pcsf.adapters import modem_to_pcsf
from pcsf.adapters.emc import emc_to_pcsf as pcsf_emc_to_pcsf
from pcsf.adapters.emc import pcsf_to_emc
from pcsf.algorithms import sample_log10
from pcsf.core.record import RECOMMENDED_FIELDS, REQUIRED_FIELDS

warnings.filterwarnings("ignore")
RAW = paths.EMC
# grid centre (lat, lon) and false northing as stated in each readme.txt
MODELS = {
    "MCR.MT.Bedrosian2016": ("MCR-MT-2016", 42.8267, -90.647, 4741799.0),
    "THO.MT.Bedrosian2021": ("THO-MT-2021", 46.5, -107.5, 5152640.0),
    "WUS.MT.Bedrosian2021": ("WUS-MT-2021", 40.75, -113.25, 4511000.0),
}


# ------------------------------------------------------------ attributes
def _attr_pack(value):
    if isinstance(value, str):
        return {"t": "str", "v": value}
    arr = np.asarray(value)
    return {"t": arr.dtype.str, "v": arr.tolist()}


def _attr_unpack(packed):
    if packed["t"] == "str":
        return packed["v"]
    return np.array(packed["v"], dtype=np.dtype(packed["t"]))


# ------------------------------------------------------------ EMC <-> PCSF
def emc_to_pcsf(path: Path):
    """EMC netCDF file to PCSF with pcsf, and its global attributes."""
    model = pcsf_emc_to_pcsf(path, created_by="pcsf.adapters.emc_to_pcsf "
                                               "(emc_roundtrip.py)")
    g = {a: _attr_unpack(p) for a, p
         in model.metadata["emc"]["global_attributes"].items()}
    model.description = (f"EMC model {g.get('id', path.stem)}: "
                         f"{g.get('title', '')}")
    return model, g


def compare_netcdf(a: Path, b: Path) -> dict:
    da, db = netCDF4.Dataset(a), netCDF4.Dataset(b)
    da.set_auto_mask(False)
    db.set_auto_mask(False)
    out = {"format_equal": da.data_model == db.data_model}
    vars_equal, attrs_equal, n_attr = True, True, 0
    for n in da.variables:
        x, y = da[n][:], db[n][:]
        vars_equal &= (x.dtype == y.dtype) and np.array_equal(x, y)
        for att in da[n].ncattrs():
            n_attr += 1
            p, q = da[n].getncattr(att), db[n].getncattr(att)
            attrs_equal &= (type(p) is type(q)) and np.array_equal(np.asarray(p), np.asarray(q))
        attrs_equal &= set(da[n].ncattrs()) == set(db[n].ncattrs())
    for att in da.ncattrs():
        n_attr += 1
        p, q = da.getncattr(att), db.getncattr(att)
        attrs_equal &= (type(p) is type(q)) and np.array_equal(np.asarray(p), np.asarray(q))
    attrs_equal &= set(da.ncattrs()) == set(db.ncattrs())
    out.update({"variables_bit_equal": bool(vars_equal), "attributes_equal": bool(attrs_equal),
                "n_attributes": n_attr})
    da.close()
    db.close()
    return out


# ------------------------------------------------------------ inversion record
def emc_record(g: dict) -> InversionRecord:
    text = " ".join(str(g.get(k, "")) for k in ("summary", "comment"))
    solver = "ModEM" if "modem" in text.lower() else "not stated in the archive file"
    return InversionRecord(
        solver=solver,
        data={"source": str(g.get("repository_pid", "")),
              "components": [], "errors": ""},
        citation={"authors": g.get("author_name"), "year": g.get("year"),
                  "title": g.get("reference", g.get("title")),
                  "doi": g.get("reference_pid"),
                  "licence": g.get("license", g.get("licence"))},
    )


# ------------------------------------------------------------ archive vs solver
def modem_pcsf(rho_path: Path):
    """Solver model read with pcsf, origin folded into the coordinates.

    The archive comparison works in absolute grid coordinates, so the
    grid origin of the .rho file is added to the cell centres and
    nodes, as in the earlier version of this script.
    """
    pc = modem_to_pcsf(rho_path, air_threshold_ohm_m=None)
    g = pc.geometry
    ox, oy = float(g.origin[0]), float(g.origin[1])
    pc.geometry = Grid3DGeometry(
        x=g.x + ox, y=g.y + oy, z=g.z,
        x_nodes=g.x_nodes + ox, y_nodes=g.y_nodes + oy,
        z_nodes=g.z_nodes)
    return pc


def archive_vs_solver(stem, label, lat0, lon0, fn, emc_model, solver):
    native = np.asarray(emc_model.resistivity_native)       # log10 sigma, nan = fill
    lon, lat, dep = emc_model.geometry.x, emc_model.geometry.y, emc_model.geometry.z
    LON, LAT = np.meshgrid(lon, lat)
    t = Transformer.from_crs(
        "EPSG:4326", f"+proj=tmerc +lat_0=0 +lon_0={lon0} +k=1 +x_0=0 +y_0=0 +ellps=WGS84",
        always_xy=True)
    E, N = t.transform(LON, LAT)
    n_centre = t.transform(lon0, lat0)[1]
    sg = solver.geometry
    lr = np.log10(np.asarray(solver.resistivity))
    rows = []
    zmax = solver.geometry.z_nodes[-1]
    keep_k = [k for k in range(dep.size) if dep[k] <= zmax]
    for lab, off in (("readme false northing", fn), ("readme grid centre", n_centre)):
        gx, gy = (N - off).ravel(), E.ravel()
        for rule in ("linear", "nearest"):
            dd = []
            if rule == "nearest":
                ix = np.clip(np.searchsorted(sg.x_nodes, gx) - 1, 0, sg.x.size - 1)
                iy = np.clip(np.searchsorted(sg.y_nodes, gy) - 1, 0, sg.y.size - 1)
                inside = ((gx >= sg.x_nodes[0]) & (gx <= sg.x_nodes[-1]) &
                          (gy >= sg.y_nodes[0]) & (gy <= sg.y_nodes[-1]))
            for k in keep_k:
                e = -native[k].ravel()
                if rule == "linear":
                    s = sample_log10(solver, np.column_stack([gx, gy, np.full(gx.size, dep[k])]))
                else:
                    kz = min(int(np.searchsorted(sg.z_nodes, dep[k]) - 1), sg.z.size - 1)
                    s = np.where(inside, lr[kz, iy, ix], np.nan)
                dd.append(e - s)
            dd = np.concatenate(dd)
            ok = np.isfinite(dd)
            d_ = dd[ok]
            rows.append({"model": label, "projection": lab, "sampling": rule,
                         "northing_offset_m": round(off - fn, 1),
                         "rms_dec": round(float(np.sqrt(np.mean(d_ ** 2))), 4),
                         "bias_dec": round(float(np.mean(d_)), 4),
                         "median_abs_dec": round(float(np.median(np.abs(d_))), 4),
                         "frac_gt_1_dec": round(float(np.mean(np.abs(d_) > 1)), 4),
                         "frac_equal_1e-4": round(float(np.mean(np.abs(d_) < 1e-4)), 4),
                         "n": int(ok.sum()), "fill_values": int(np.isnan(native).sum())})
            print(rows[-1])
    # horizontal cells of the solver grid whose centre falls inside the archive box
    inv = Transformer.from_crs(t.target_crs, "EPSG:4326", always_xy=True)
    XC, YC = np.meshgrid(sg.x, sg.y, indexing="ij")
    lo, la = inv.transform(YC, XC + fn)
    inside = ((lo >= lon.min()) & (lo <= lon.max()) & (la >= lat.min()) & (la <= lat.max()))
    return rows, {"model": label, "solver_cells_h": int(inside.size),
                  "solver_cells_h_inside_archive": int(inside.sum()),
                  "solver_nz": int(sg.z.size), "archive_nz": int(dep.size),
                  "archive_nz_within_solver_depth": len(keep_k),
                  "archive_grid": f"{lat.size} x {lon.size} x {dep.size}",
                  "solver_grid": f"{sg.x.size} x {sg.y.size} x {sg.z.size}"}


# ------------------------------------------------------------ figure
def _panel_fields(label, lat0, lon0, offset, rule, emc_model, solver, depth_km):
    lon, lat, dep = emc_model.geometry.x, emc_model.geometry.y, emc_model.geometry.z
    k = int(np.argmin(np.abs(dep - depth_km * 1000)))
    LON, LAT = np.meshgrid(lon, lat)
    t = Transformer.from_crs(
        "EPSG:4326", f"+proj=tmerc +lat_0=0 +lon_0={lon0} +k=1 +x_0=0 +y_0=0 +ellps=WGS84",
        always_xy=True)
    E, N = t.transform(LON, LAT)
    sg = solver.geometry
    gx, gy = (N - offset).ravel(), E.ravel()
    if rule == "nearest":
        ix = np.clip(np.searchsorted(sg.x_nodes, gx) - 1, 0, sg.x.size - 1)
        iy = np.clip(np.searchsorted(sg.y_nodes, gy) - 1, 0, sg.y.size - 1)
        kz = min(int(np.searchsorted(sg.z_nodes, dep[k]) - 1), sg.z.size - 1)
        s = np.log10(np.asarray(solver.resistivity))[kz, iy, ix].reshape(LON.shape)
    else:
        s = sample_log10(solver, np.column_stack([gx, gy, np.full(gx.size, dep[k])])
                         ).reshape(LON.shape)
    a = -np.asarray(emc_model.resistivity_native)[k]
    return lon, lat, dep[k], s, a


def figure(cases, depth_km=15.0):
    """cases: list of (label, lat0, lon0, northing offset, rule, emc_model, solver)."""
    fs.apply()
    fig = plt.figure(figsize=(fs.DOUBLE, 0.62 * fs.DOUBLE))
    gs = fig.add_gridspec(len(cases) + 1, 3, height_ratios=[1] * len(cases) + [0.05],
                          hspace=0.42, wspace=0.10)
    norm = Normalize(0.5, 4.0)
    dnorm = TwoSlopeNorm(0, -1, 1)
    titles = ["ModEM solver file, resampled", "EMC archive file", "Archive minus solver"]
    for i, case in enumerate(cases):
        label, lat0, lon0, off, rule, emc_model, solver = case
        lon, lat, z, s, a = _panel_fields(label, lat0, lon0, off, rule, emc_model, solver,
                                          depth_km)
        d = a - s
        frac = float(np.mean(np.abs(d[np.isfinite(d)]) < 1e-4))
        for j, f in enumerate((s, a, d)):
            ax = fig.add_subplot(gs[i, j])
            if j < 2:
                im = ax.pcolormesh(lon, lat, f, cmap=fs.RES_CMAP, norm=norm,
                                   shading="nearest", rasterized=True)
            else:
                imd = ax.pcolormesh(lon, lat, f, cmap=fs.DIFF_CMAP, norm=dnorm,
                                    shading="nearest", rasterized=True)
                ax.text(0.98, 0.04, f"{100 * frac:.0f}% of cells equal",
                        transform=ax.transAxes, ha="right", va="bottom", fontsize=5.8,
                        bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.2))
            ax.set_aspect(1 / np.cos(np.radians(lat.mean())))
            if i == 0:
                ax.set_title(titles[j], loc="left", pad=3)
            if j == 0:
                ax.set_ylabel(f"{label}\nLatitude (deg)")
            else:
                plt.setp(ax.get_yticklabels(), visible=False)
            ax.set_xlabel("Longitude (deg)")
            fs.boxed_spines(ax)
            fs.panel_label(ax, "abcdef"[3 * i + j])
        fig.axes[-3].text(0.02, 0.04, f"{z / 1000:.1f} km; solver {'nearest cell' if rule == 'nearest' else 'linear interpolation'}",
                          transform=fig.axes[-3].transAxes, fontsize=5.8, va="bottom",
                          bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.2))
    cax = fig.add_subplot(gs[-1, 0:2])
    pos = cax.get_position()
    cax.set_position([pos.x0 + 0.08, pos.y0 - 0.02, pos.width - 0.16, pos.height])
    fs.log_rho_colorbar(fig, im, cax, orientation="horizontal")
    cax = fig.add_subplot(gs[-1, 2])
    pos = cax.get_position()
    cax.set_position([pos.x0 + 0.02, pos.y0 - 0.02, pos.width - 0.04, pos.height])
    cb = fig.colorbar(imd, cax=cax, orientation="horizontal", ticks=[-1, -0.5, 0, 0.5, 1])
    cb.set_label(r"$\Delta$ (decades)")
    cb.outline.set_linewidth(0.5)
    fs.save(fig, "emc_vs_solver")


# ------------------------------------------------------------ main
def main():
    trip, comp, cover, recs, cases = [], [], [], [], {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for stem, (label, lat0, lon0, fn) in MODELS.items():
            src = RAW / f"{stem}.resistivity.r0.0-n4c.nc"
            model, g = emc_to_pcsf(src)
            rec = emc_record(g)
            attach_inversion_record(model, rec)
            miss = check_inversion_record(rec)
            recs.append({"model": label,
                         "required_present": len(REQUIRED_FIELDS) - len(miss["required"]),
                         "recommended_present": len(RECOMMENDED_FIELDS) - len(miss["recommended"]),
                         "missing_required": ";".join(miss["required"]),
                         "citation_doi": rec.citation.get("doi"),
                         "licence": rec.citation.get("licence")})
            p1 = write_pcsf(model, tmp / f"{stem}.pcsf")
            p2 = write_pcsm(read_pcsf(p1), tmp / f"{stem}.pcsm")
            p3 = write_pcsf(read_pcsm(p2), tmp / f"{stem}.back.pcsf")
            back = tmp / f"{stem}.back.nc"
            pcsf_to_emc(read_pcsf(p3), back)
            res = compare_netcdf(src, back)
            nat = np.asarray(model.resistivity_native)
            trip.append({"model": label, "grid": "x".join(map(str, nat.shape)),
                         "values": int(nat.size), "fill_values": int(np.isnan(nat).sum()),
                         "pcsf_mb": round(p1.stat().st_size / 1e6, 2),
                         "pcsm_mb": round(p2.stat().st_size / 1e6, 2),
                         "netcdf_mb": round(src.stat().st_size / 1e6, 2), **res})
            print(trip[-1])

            solver = modem_pcsf(RAW / f"{stem}.resistivity" / f"{stem}.resistivity.rho")
            rows, cov = archive_vs_solver(stem, label, lat0, lon0, fn, model, solver)
            comp += rows
            cover.append(cov)
            print(cov)
            if stem.startswith("WUS"):
                # best reading for WUS: grid centre, nearest cell (Part B)
                t = Transformer.from_crs("EPSG:4326", f"+proj=tmerc +lat_0=0 +lon_0={lon0} "
                                         "+k=1 +x_0=0 +y_0=0 +ellps=WGS84", always_xy=True)
                cases["WUS"] = (label, lat0, lon0, t.transform(lon0, lat0)[1], "nearest",
                                model, solver)
            if stem.startswith("MCR"):
                cases["MCR"] = (label, lat0, lon0, fn, "linear", model, solver)

    figure([cases["WUS"], cases["MCR"]])
    for name, rows in (("emc_roundtrip", trip), ("emc_vs_solver", comp),
                       ("emc_coverage", cover), ("emc_records", recs)):
        with (fs.RESULTS / f"{name}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(json.dumps(recs, indent=1))


if __name__ == "__main__":
    main()
