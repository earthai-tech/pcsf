"""Rebuild every PCSF/PCSM model of the paper from the native runs.

Tier 2 of the reproduction (``run_all.py --rebuild``); it needs
pyCSAMT for the EDI station tables, the Occam2D and MARE2DEM result
objects and the multi-line assembly. Writes into ``paths.MODELS``
(``output/models`` during a rebuild):

  tongkeng_occam2d.pcsf            Occam2D, Tongkeng CSAMT (bundled example)
  baohuashan_modem3d_sample.pcsf   ModEM 3-D, bundled 27-frequency sample run
  mare2dem_demo.pcsf               MARE2DEM demonstration inversion
  synthetic_unet.pcsf              generic adapter, synthetic 2-D prediction
  synthetic_gcn.pcsf               generic adapter, synthetic mesh prediction
  baohuashan_occam2d_L{18..34}.pcsf  Occam2D, one file per Baohuashan line,
                                   with station lon/lat and elevation
  baohuashan_multiline.pcsf        the five lines as one multiline model
  baohuashan_modem3d.pcsf          ModEM 3-D, converged run used for the
                                   2-D/3-D comparison
and a .pcsm sibling of each. A summary is written to
``results/field_models.csv``.

Inputs, all in the data archive (``paths``): the native runs under
``native/``, the processed EDI files under ``edi/``, and under
``rebuild/`` the earlier conversions that carry the station tables
and the two synthetic predictions.
"""

from __future__ import annotations

import csv
import shutil
import warnings
from pathlib import Path

import numpy as np

import figstyle as fs
import paths
from pycsamt.emtools import ensure_sites
from pcsf import read_pcsf, write_pcsf, write_pcsm
from pcsf.adapters import mare2dem_to_pcsf, modem_to_pcsf, occam2d_to_pcsf
from pycsamt.format import build_multiline_pcsf
from pycsamt.models.occam2d import InversionResult
from pycsamt.topo.extract import _read_latlon, extract_elevation, extract_station_names

warnings.filterwarnings("ignore")

EDI_ROOT = paths.EDI
OCCAM = paths.OCCAM_BAOHUASHAN
LINES = ["L18", "L22", "L26", "L30", "L34"]

COPIES = {
    "tongkeng_occam2d": paths.REBUILD / "tongkeng_occam2d_with_topo.pcsf",
    "synthetic_unet": paths.REBUILD / "synthetic_unet.pcsf",
    "synthetic_gcn": paths.REBUILD / "synthetic_gcn.pcsf",
}


#: ModEM runs: (name, converted file with the survey's station table,
#: final model, NLCG log). Arrays and geometry are read from the .rho
#: file by pcsf; stations, topography and descriptions come from the
#: earlier conversion, which matched them to the EDI files.
MODEM = {
    "baohuashan_modem3d": (
        paths.REBUILD / "modem_baohuashan_stations.pcsf",
        paths.MODEM_FIELD / "stageA_v5_NLCG_113.rho",
        paths.MODEM_FIELD / "stageA_v5_NLCG.log",
    ),
    "baohuashan_modem3d_sample": (
        paths.REBUILD / "modem_sample_stations.pcsf",
        paths.MODEM_SAMPLE / "Modular_NLCG_073.rho",
        paths.MODEM_SAMPLE / "Modular_NLCG.log",
    ),
}


def build_modem(name: str, path: Path) -> dict:
    """Convert a ModEM run with pcsf and keep the survey's stations.

    The earlier conversions (August 2026) stored each .rho row in file
    order. ModEM writes x from north to south (WS.inc reads
    ``(rho%v(i,j,k), i=Nx,1,-1)``), so those volumes were mirrored
    north-south with respect to their stations. The check below
    records that relation before the corrected volume replaces it.
    Air masking and the station Z convention are left as in the
    earlier files, so that orientation is the only difference.
    """
    src, rho, log = MODEM[name]
    old = read_pcsf(src)
    new = modem_to_pcsf(
        rho, log=log, air_threshold_ohm_m=None,
        station_z_convention="elevation",
        created_by="pcsf.adapters.modem_to_pcsf (build_field_models.py)",
        description=old.description, crs=old.crs,
    )
    for axis in ("x", "y", "z", "x_nodes", "y_nodes", "z_nodes", "origin"):
        assert np.array_equal(getattr(new.geometry, axis),
                              getattr(old.geometry, axis)), (name, axis)
    mirrored = bool(np.array_equal(old.resistivity_native,
                                   new.resistivity_native[:, :, ::-1]))
    unchanged = bool(np.array_equal(old.resistivity_native,
                                    new.resistivity_native))
    new.stations, new.topography = old.stations, old.topography
    new.survey = dict(old.survey)
    new.metadata = {**{k: v for k, v in old.metadata.items()
                       if k not in ("inversion",)},
                    **new.metadata,
                    "orientation": "x increases northward"}
    write_pcsf(new, path)
    return {"file": name, "old_was_mirrored": mirrored,
            "old_equal_new": unchanged, "rho_file": rho.name}


def key(name: str) -> str:
    """Station key shared by the EDI, Occam2D and ModEM names (e.g. 18-023)."""
    return str(name)[:6]


def edi_station_table(line: str) -> dict[str, tuple[float, float, float]]:
    sites = ensure_sites(EDI_ROOT / f"{line}PLT", recursive=False)
    names = extract_station_names(sites)
    elev = extract_elevation(sites)
    latlon = _read_latlon(sites)
    return {key(n): (lo, la, z) for n, (la, lo), z in zip(names, latlon, elev)}


def build_occam_line(line: str):
    wd = OCCAM / f"{line}PLT"
    table = edi_station_table(line)
    names = list(occam2d_to_pcsf(wd).stations.name)
    lonlat = {n: table[key(n)][:2] for n in names if key(n) in table}
    elev = {n: table[key(n)][2] for n in names if key(n) in table}
    model = occam2d_to_pcsf(
        wd,
        station_lonlat=lonlat,
        station_elevations=elev,
        created_by="pcsf.adapters.occam2d_to_pcsf (build_field_models.py)",
    )
    rms = model.metadata["final_rms"]
    model.description = (f"Occam2D inversion of Baohuashan AMT line {line} "
                         f"(final RMS {rms:.2f})")
    return model, rms


def convert_mare2dem(path: Path) -> None:
    """Convert the final MARE2DEM iteration with the current adapter.

    The mesh is triangulated from demo.poly with the Triangle generator
    ('pA': keep the input segments, assign region attributes), exactly as
    in examples/pcsf_conversion_demo.
    """
    wd = paths.MARE2DEM
    final = sorted(wd.glob("demo.*.resistivity"),
                   key=lambda p: int(p.name.split(".")[1]))[-1]
    model = mare2dem_to_pcsf(
        final, log=wd / "demo.logfile",
        created_by="pcsf.adapters.mare2dem_to_pcsf (build_field_models.py)",
        description=(f"MARE2DEM demo_mt_inversion, final iteration "
                     f"{final.name}, real mesh and per-region resistivity"))
    write_pcsf(model, path)


def add_tongkeng_topography(path: Path) -> None:
    """Attach the surveyed Tongkeng station elevations and positions.

    The Occam2D run carries no coordinates. The survey station file
    data/avg/k1.stn (UTM zone 49N easting/northing and elevation, 50 m
    station spacing) is the same profile; elevation and position are
    interpolated at each Occam2D station chainage along the surveyed path.
    """
    from pyproj import Transformer

    from pcsf import TopographyPerStation

    raw = np.genfromtxt(paths.REBUILD / "tongkeng_k1.stn", delimiter=",", skip_header=1)
    e, n, h = raw[:, 1], raw[:, 2], raw[:, 3]
    chain = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(e), np.diff(n)))])
    model = read_pcsf(path)
    st = model.stations
    x = np.asarray(st.x, float)
    elev = np.interp(x, chain, h)
    lon, lat = Transformer.from_crs("EPSG:32649", "EPSG:4326", always_xy=True).transform(
        np.interp(x, chain, e), np.interp(x, chain, n))
    st.z = elev
    st.lon = np.asarray(lon)
    st.lat = np.asarray(lat)
    model.topography = TopographyPerStation(station_id=list(st.name), elevation=elev)
    model.description = ("Tongkeng CSAMT Occam2D model (47 stations); station "
                         "elevation and position interpolated by chainage from "
                         "the survey station file k1.stn (UTM 49N)")
    write_pcsf(model, path)


def attach_records(rows) -> None:
    """Attach the inversion record of every file and report its completeness
    (results/inversion_records.csv)."""
    import json

    import inversion_records as ir
    from pcsf import attach_inversion_record, check_inversion_record
    from pcsf.core.record import RECOMMENDED_FIELDS, REQUIRED_FIELDS
    from pycsamt.models.mare2dem.results import InversionResult as M2Result

    doi = ir.all_doi()
    table = []
    for name, path in rows:
        model = read_pcsf(path)
        if name.startswith("baohuashan_occam2d_"):
            line = name.rsplit("_", 1)[1]
            rec = ir.occam_baohuashan(line, InversionResult(OCCAM / f"{line}PLT"), doi)
        elif name == "baohuashan_multiline":
            rec = ir.occam_baohuashan("L18", InversionResult(OCCAM / "L18PLT"), doi)
            rec.data["source"] = "processed EDI files, Baohuashan lines L18-L34"
            rec.data["n_stations"] = len(model.stations.name)
            rec.misfit = {"final_rms": "per line (7.58-10.37)", "target_rms": 1.0,
                          "termination": "unknown",
                          "n_iterations": "per line (22-55)"}
            rec.regularization["trade_off"] = "per line"
            rec.reliability["depth_of_investigation_m"] = {
                s: doi[key(s)] for s in model.stations.name if key(s) in doi}
        elif name == "baohuashan_modem3d":
            rec = ir.modem_baohuashan(doi, list(model.stations.name))
        elif name == "baohuashan_modem3d_sample":
            rec = ir.modem_sample()
        elif name == "tongkeng_occam2d":
            rec = ir.occam_tongkeng(InversionResult(paths.TONGKENG))
        elif name == "mare2dem_demo":
            rec = ir.mare2dem_demo(M2Result(workdir=paths.MARE2DEM))
        else:
            rec = ir.synthetic("UNet" if "unet" in name else "graph network")
        attach_inversion_record(model, rec)
        write_pcsf(model, path)
        miss = check_inversion_record(rec)
        table.append({"file": name, "solver": rec.solver,
                      "required_present": len(REQUIRED_FIELDS) - len(miss["required"]),
                      "required_total": len(REQUIRED_FIELDS),
                      "recommended_present": len(RECOMMENDED_FIELDS) - len(miss["recommended"]),
                      "recommended_total": len(RECOMMENDED_FIELDS),
                      "missing_required": ";".join(miss["required"]),
                      "termination": rec.misfit.get("termination", ""),
                      "final_rms": rec.misfit.get("final_rms", "")})
        print("record:", table[-1]["file"], table[-1]["required_present"], "/",
              len(REQUIRED_FIELDS), miss["required"])
    with (fs.RESULTS / "inversion_records.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    with (fs.RESULTS / "depth_of_investigation.json").open("w") as fh:
        json.dump(doi, fh, indent=1)


def main():
    rows = []
    for name, src in COPIES.items():
        dst = fs.DATA / f"{name}.pcsf"
        shutil.copyfile(src, dst)
        rows.append((name, dst))

    modem_rows = []
    for name in MODEM:
        dst = fs.DATA / f"{name}.pcsf"
        modem_rows.append(build_modem(name, dst))
        rows.append((name, dst))
        print("modem:", modem_rows[-1])
    with (fs.RESULTS / "modem_orientation.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(modem_rows[0]))
        w.writeheader()
        w.writerows(modem_rows)

    add_tongkeng_topography(fs.DATA / "tongkeng_occam2d.pcsf")
    convert_mare2dem(fs.DATA / "mare2dem_demo.pcsf")
    rows.append(("mare2dem_demo", fs.DATA / "mare2dem_demo.pcsf"))

    profiles = {}
    for line in LINES:
        model, rms = build_occam_line(line)
        dst = fs.DATA / f"baohuashan_occam2d_{line}.pcsf"
        write_pcsf(model, dst)
        rows.append((dst.stem, dst))
        st = model.stations
        profiles[line] = {
            "x": model.geometry.x, "z": model.geometry.z, "rho": model.resistivity,
            "sta_x": st.x, "sta_names": list(st.name), "sta_elev": st.z,
            "sta_lat": st.lat, "sta_lon": st.lon,
        }
        print(f"{line}: {len(st.name)} stations, rms {rms:.2f}, "
              f"shape {model.resistivity.shape}")

    multi = build_multiline_pcsf(
        profiles, source_backend="occam2d",
        created_by="pyCSAMT build_field_models.py",
        description="Five Occam2D lines of the Baohuashan AMT survey",
    )
    dst = fs.DATA / "baohuashan_multiline.pcsf"
    write_pcsf(multi, dst)
    rows.append((dst.stem, dst))

    attach_records(rows)

    out = []
    for name, path in rows:
        model = read_pcsf(path)
        pcsm = path.with_suffix(".pcsm")
        write_pcsm(model, pcsm)
        if model.kind == "multiline":
            n_cells = sum(np.asarray(l.resistivity).size for l in model.geometry.lines)
            shape = f"{len(model.geometry.lines)} lines"
        else:
            n_cells = int(np.asarray(model.resistivity).size)
            shape = "x".join(map(str, np.asarray(model.resistivity).shape))
        n_st = 0 if model.stations is None else len(model.stations.name)
        out.append({"name": name, "kind": model.kind, "source": model.source_backend,
                    "shape": shape, "n_cells": n_cells, "n_stations": n_st,
                    "pcsf_bytes": path.stat().st_size, "pcsm_bytes": pcsm.stat().st_size})
        print(out[-1])
    with (fs.RESULTS / "field_models.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)


if __name__ == "__main__":
    main()
