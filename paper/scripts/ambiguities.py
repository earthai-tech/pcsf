"""Ambiguities met in the manuscript's own solver files, and the error each
one causes when a reader resolves it wrongly.

Every case compares the correct reading of a model with a plausible wrong
reading, in log10 resistivity (decades), with pcsf.algorithms.sample_log10.

A1  ModEM natural-log values read as log10 (encoding).
A2  Occam2D log10 values read as natural log (encoding).
A3  ModEM north-first horizontal axes read as east-first (axis order).
A4  ModEM station depth ignored: profiles start at the model top, 224 m
    a.s.l., a value stated only in a comment of the data file (datum).
A5  ModEM air cells (1e11-1e13 ohm m) not removed before interpolation
    (near-surface contamination).
A6  Occam2D mesh-local horizontal coordinate read as station chainage
    (origin offset; Tongkeng and Baohuashan L18).
A7  MARE2DEM starting model read in place of the final iteration
    (wrong file).

Output: results/ambiguities.csv
"""

from __future__ import annotations

import csv
import warnings

import numpy as np

import figstyle as fs
import paths
from pcsf.native.occam2d import read_mesh
from field_2d_vs_3d import registration
from pcsf import PCSFModel, read_pcsf
from pcsf.algorithms import sample_log10

warnings.filterwarnings("ignore")
AIR = 1e8


def stats(a, b):
    d = np.asarray(a, float) - np.asarray(b, float)
    ok = np.isfinite(d)
    n_all = d.size
    d = d[ok]
    return {"rms_dec": float(np.sqrt(np.mean(d * d))), "mean_abs_dec": float(np.mean(np.abs(d))),
            "max_abs_dec": float(np.max(np.abs(d))), "n": int(ok.sum()),
            "undefined_frac": float(1 - ok.sum() / n_all)}


def station_columns(m3, depths, swap=False, from_top=False, mask_air=True):
    """log10 rho of the ModEM model below every station, at depths below
    the surface (or below the model top if from_top)."""
    to_grid, surf, _ = registration(m3)
    st = m3.stations
    gx, gy = to_grid(st.lon, st.lat)
    if swap:
        gx, gy = gy, gx
    z0 = np.zeros_like(st.z) if from_top else np.asarray(st.z, float)
    G = np.repeat(np.column_stack([gx, gy]), depths.size, axis=0)
    Z = (z0[:, None] + depths[None, :]).ravel()
    model = m3
    if mask_air:
        # Correct reading: air cells take the value of the first earth cell
        # below them, so that a point just below the surface interpolates
        # between earth values only.
        rho = np.asarray(m3.resistivity, float).copy()
        air = rho > AIR
        first = np.argmax(~air, axis=0)                       # (ny, nx)
        top = np.take_along_axis(rho, first[None], axis=0)[0]
        rho = np.where(air, top[None], rho)
        model = PCSFModel(geometry=m3.geometry, resistivity=rho)
    return sample_log10(model, np.column_stack([G, Z])).reshape(len(gx), depths.size)


def main():
    rows = []
    m3 = read_pcsf(fs.DATA / "baohuashan_modem3d.pcsf")
    rho3 = np.asarray(m3.resistivity, float)
    earth = rho3 < AIR

    # A1: ln read as log10
    r = np.asarray(m3.resistivity_native, float)[earth]
    rows.append({"case": "A1", "file": "ModEM (Baohuashan)",
                 "ambiguity": "natural-log values read as log10",
                 **stats(r, r / np.log(10))})

    # A2: log10 read as ln
    m2 = read_pcsf(fs.DATA / "baohuashan_occam2d_L18.pcsf")
    r2 = np.asarray(m2.resistivity_native, float).ravel()
    rows.append({"case": "A2", "file": "Occam2D (Baohuashan L18)",
                 "ambiguity": "log10 values read as natural log",
                 **stats(r2 / np.log(10), r2)})

    depths = np.arange(0.0, 1000.0 + 1e-6, 10.0)
    ref = station_columns(m3, depths)
    # A3: axis order
    rows.append({"case": "A3", "file": "ModEM (Baohuashan)",
                 "ambiguity": "north-first axes read as east-first",
                 **stats(station_columns(m3, depths, swap=True), ref)})
    # A4: depth datum
    rows.append({"case": "A4", "file": "ModEM (Baohuashan)",
                 "ambiguity": "station depth ignored (profiles start at model top)",
                 **stats(station_columns(m3, depths, from_top=True, mask_air=False), ref)})
    # A5: air cells kept, top 100 m
    d100 = np.arange(0.0, 100.0 + 1e-6, 5.0)
    rows.append({"case": "A5", "file": "ModEM (Baohuashan)",
                 "ambiguity": "air cells not removed (0-100 m below surface)",
                 **stats(station_columns(m3, d100, mask_air=False),
                         station_columns(m3, d100))})

    # A6: Occam2D mesh-local coordinate
    # The mesh-local origin of Occam2D lies N_PAD padding columns to
    # the left of the first station (7 for meshes built by pyCSAMT and
    # MTpy, the two runs here).
    N_PAD = 7
    for label, stem, wd in (("Tongkeng", "tongkeng_occam2d", paths.TONGKENG),
                            ("Baohuashan L18", "baohuashan_occam2d_L18",
                             paths.OCCAM_BAOHUASHAN / "L18PLT")):
        m = read_pcsf(fs.DATA / f"{stem}.pcsf")
        mesh = read_mesh(paths.require(wd / "Occam2DMesh"))
        pad = float(np.sum(mesh.x_widths[:N_PAD]))
        sx = np.asarray(m.stations.x, float)
        D = np.arange(0.0, 1000.0 + 1e-6, 10.0)
        X, Zd = np.meshgrid(sx, D)
        good = sample_log10(m, np.column_stack([X.ravel(), Zd.ravel()]))
        bad = sample_log10(m, np.column_stack([(X - pad).ravel(), Zd.ravel()]))
        rows.append({"case": "A6", "file": f"Occam2D ({label})",
                     "ambiguity": f"mesh-local x read as chainage (offset {pad / 1e3:.1f} km)",
                     **stats(bad, good)})

    # A7: starting model instead of final iteration (per region, free regions)
    def rho_col(path):
        vals, free, on = [], [], False
        for ln in path.read_text().splitlines():
            if ln.strip().startswith("!#"):
                on = True
                continue
            if on and ln.strip():
                p = ln.split()
                vals.append(float(p[1]))
                free.append(int(p[2]) > 0)
        return np.array(vals), np.array(free)
    wd = paths.require(paths.MARE2DEM)
    v6, free6 = rho_col(wd / "demo.6.resistivity")
    v0, _ = rho_col(wd / "demo.0.resistivity")
    rows.append({"case": "A7", "file": "MARE2DEM (demonstration)",
                 "ambiguity": "starting model read instead of final iteration",
                 **stats(np.log10(v0[free6]), np.log10(v6[free6]))})

    for r_ in rows:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r_.items()})
    with (fs.RESULTS / "ambiguities.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
