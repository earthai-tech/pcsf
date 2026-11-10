"""Inversion records (critical inversion metadata) for the manuscript files,
and the Niblett-Bostick depth of investigation of the Baohuashan stations.

Every value below is read from the run files or stated in them; values that
the run files do not contain are left empty, so that
pcsf.check_inversion_record reports them as missing.
"""

from __future__ import annotations

import csv
import re
import warnings
from pathlib import Path

import numpy as np

import figstyle as fs  # noqa: F401
import paths
from pcsf import InversionRecord

warnings.filterwarnings("ignore")
EDI_ROOT = paths.EDI
MODEM_STUDENT = paths.MODEM_FIELD
LINES = ["L18", "L22", "L26", "L30", "L34"]
#: Models of the data archive, whose records stand in for the inputs
#: of lines whose measured data are withheld.
ARCHIVED = paths.DATA / "models"
NB_CONST = 356.0  # sqrt(1 / (2 pi mu0)) in m / sqrt(ohm m s)


def key(name: str) -> str:
    return str(name)[:6]


# ------------------------------------------------------------ depth of investigation
def nb_depth_of_investigation(line: str) -> dict[str, float]:
    """Niblett-Bostick depth of the determinant apparent resistivity,
    maximum over frequency, for every station of a line (metres).

        rho_a(T) = 0.2 T |Z_det|^2,   Z_det = sqrt(Zxx Zyy - Zxy Zyx)
        h(T)     = sqrt(rho_a T / (2 pi mu0)) = 356 sqrt(rho_a T)

    Z in mV/km/nT (EDI field units), T in s.
    """
    from pycsamt.emtools import ensure_sites

    out = {}
    for st in ensure_sites(EDI_ROOT / f"{line}PLT", recursive=False):
        z, T = st.z, 1.0 / st.freq
        zdet = np.sqrt(z[:, 0, 0] * z[:, 1, 1] - z[:, 0, 1] * z[:, 1, 0])
        rho_a = 0.2 * T * np.abs(zdet) ** 2
        out[key(st.name)] = float(np.nanmax(NB_CONST * np.sqrt(rho_a * T)))
    return out


def has_line_data(line: str) -> bool:
    """Whether the measured data of a Baohuashan line are available.

    Only lines L18 and L22 are public; the archive holds the models
    of the other lines but not their EDI files or Occam2D data files.
    """
    return ((EDI_ROOT / f"{line}PLT").is_dir()
            and (paths.OCCAM_BAOHUASHAN / f"{line}PLT"
                 / "OccamDataFile.dat").is_file())


def archived_record(name: str) -> InversionRecord:
    """Inversion record of an archived model (``data/models``)."""
    from pcsf import get_inversion_record, read_pcsf

    rec = get_inversion_record(read_pcsf(ARCHIVED / f"{name}.pcsf"))
    if rec is None:
        raise SystemExit(f"{name}.pcsf in {ARCHIVED} has no record")
    return rec


def all_doi() -> dict[str, float]:
    """Depth of investigation of every Baohuashan station (m).

    Computed from the EDI files where they are available; for lines
    whose data are withheld, read from the archived model's record.
    """
    d = {}
    for line in LINES:
        if has_line_data(line):
            d.update(nb_depth_of_investigation(line))
            continue
        rec = archived_record(f"baohuashan_occam2d_{line}")
        doi = rec.reliability["depth_of_investigation_m"]
        d.update({key(s): float(v) for s, v in doi.items()})
    return d


# ------------------------------------------------------------ helpers
def _occam_freq_and_types(result):
    f = np.asarray(result.data.frequencies, float)
    types = sorted(set(np.asarray(result.data.data_blocks)[:, 2].astype(int)))
    names = {1: "TE log10 rho", 2: "TE phase", 5: "TM log10 rho", 6: "TM phase",
             3: "Tipper real", 4: "Tipper imag", 9: "TE rho", 10: "TM rho"}
    return f, [names.get(t, f"type {t}") for t in types]


def _run_summary():
    with (paths.TABLES / "occam2d_run_summary.csv").open() as fh:
        return {r["line"]: r for r in csv.DictReader(fh)}


# ------------------------------------------------------------ records
def occam_baohuashan(line: str, result, doi: dict) -> InversionRecord:
    run = _run_summary()[line]
    f, comps = _occam_freq_and_types(result)
    exit_code = int(run["exit_code"])
    term = "time_limit" if exit_code == -9 else (
        "target_reached" if float(run["final_rms"]) <= 1.0 else "stalled")
    st = list(result.data.sites)
    return InversionRecord(
        solver="Occam2D", solver_version="Occam2D 3.0 (pyCSAMT driver)",
        data={"components": comps, "frequency_range_hz": [float(f"{f.min():.6g}"), float(f"{f.max():.6g}")],
              "n_frequencies": int(f.size), "n_stations": len(st),
              "errors": "floor 10 % of apparent resistivity, 2.86 deg phase",
              "sign_convention": "exp(+i omega t) (EDI)",
              "source": f"processed EDI files, Baohuashan line {line} (27 frequencies)"},
        forward={"dimensionality": "2D",
                 "mesh": f"{result.mesh.x_widths.size} x {result.mesh.z_widths.size} mesh cells"},
        regularization={"type": "Occam smoothness (first-derivative roughness)",
                        "trade_off": float(result.best_iter.lagrange_value),
                        "start_model": "100 ohm m half-space"},
        misfit={"final_rms": float(run["final_rms"]), "target_rms": 1.0,
                "n_iterations": int(run["n_iterations"]), "termination": term},
        reliability={"method": "Niblett-Bostick depth of the determinant apparent "
                               "resistivity at the lowest frequency",
                     "depth_of_investigation_m": {s: doi.get(key(s)) for s in st
                                                  if doi.get(key(s)) is not None}},
        citation={"authors": "Kouabena, K. A. W., et al.", "year": 2025,
                  "title": "Baohuashan Cu-Mo porphyry AMT survey",
                  "doi": "10.1016/j.oregeorev.2025.106798"},
    )


def occam_tongkeng(result) -> InversionRecord:
    f, comps = _occam_freq_and_types(result)
    bi = result.best_iter
    return InversionRecord(
        solver="Occam2D",
        data={"components": comps, "frequency_range_hz": [float(f"{f.min():.6g}"), float(f"{f.max():.6g}")],
              "n_frequencies": int(f.size), "n_stations": len(result.data.sites),
              "source": "Tongkeng CSAMT profile, Occam2D data file (prepared with MTpy)"},
        forward={"dimensionality": "2D"},
        regularization={"type": "Occam smoothness (first-derivative roughness)",
                        "trade_off": float(bi.lagrange_value),
                        "start_model": "uniform half-space (Startup file)"},
        misfit={"final_rms": float(result.final_rms), "target_rms": 1.0,
                "n_iterations": int(bi.iteration), "termination": "target_reached"},
        citation={"authors": "Kouadio, K. L., et al.", "year": 2020,
                  "doi": "10.1016/j.jappgeo.2020.104204"},
    )


def _modem_log_tail(path: Path):
    txt = path.read_text(errors="replace")
    rms = [float(x) for x in re.findall(r"rms=\s*([0-9.Ee+-]+)", txt)]
    lam = [float(x) for x in re.findall(r"lambda=\s*([0-9.Ee+-]+)", txt)]
    it = [int(x) for x in re.findall(r"Completed NLCG iteration\s+(\d+)", txt)]
    stalled = "local minimum" in txt
    return rms[-1], lam[-1], (it[-1] if it else None), stalled


def _modem_data(path: Path):
    per, comps, sites, rel = set(), set(), set(), []
    sign = None
    for ln in path.read_text().splitlines():
        if ln.startswith(">") and "omega" in ln:
            sign = ln[1:].strip()
        p = ln.split()
        if len(p) >= 11 and not ln.startswith("#") and p[7] in ("ZXX", "ZXY", "ZYX", "ZYY"):
            per.add(float(p[0]))
            comps.add(p[7])
            sites.add(p[1])
            rel.append(float(p[10]) / max(np.hypot(float(p[8]), float(p[9])), 1e-30))
    f = 1.0 / np.array(sorted(per))
    r = np.percentile(np.array(rel) * 100, [5, 50, 95])
    return (f, sorted(comps), len(sites), sign,
            f"{r[0]:.0f}-{r[2]:.0f} % of |Z| (5th-95th percentile), median {r[1]:.0f} %")


def _modem_ctrl(path: Path):
    vals = {}
    for ln in path.read_text().splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            vals[k.strip()] = v.strip()
    return vals


def modem_baohuashan(doi: dict, station_names) -> InversionRecord:
    f, comps, ns, sign, errs = _modem_data(MODEM_STUDENT / "ModEMData_v5_offdiag.dat")
    ctrl = _modem_ctrl(MODEM_STUDENT / "stageA_v5.inv")
    rms, lam, it, stalled = _modem_log_tail(MODEM_STUDENT / "stageA_v5_NLCG.log")
    return InversionRecord(
        solver="ModEM", solver_version="ModEM 3D MT, NLCG",
        data={"components": comps, "frequency_range_hz": [float(f"{f.min():.6g}"), float(f"{f.max():.6g}")],
              "n_frequencies": int(f.size), "n_stations": ns, "errors": errs,
              "sign_convention": sign,
              "source": "ModEMData_v5_offdiag.dat (off-diagonal impedance); "
                        "station depth Z below a model top at 224 m a.s.l. "
                        "(stated only in a comment of the data file)"},
        forward={"dimensionality": "3D", "mesh": "91 x 54 x 44 cells (N x E x Z)"},
        regularization={"type": "ModEM model covariance (smoothing), NLCG",
                        "trade_off": lam, "start_model": "prior_v5.rho"},
        misfit={"final_rms": rms,
                "target_rms": float(ctrl.get("Exit search when rms is less than", "nan")),
                "n_iterations": it, "termination": "stalled" if stalled else "unknown"},
        reliability={"method": "Niblett-Bostick depth of the determinant apparent "
                               "resistivity at the lowest frequency (EDI, 42.1 Hz)",
                     "depth_of_investigation_m": {s: doi[key(s)] for s in station_names
                                                  if key(s) in doi}},
        citation={"authors": "Kouabena, K. A. W., et al.", "year": 2025,
                  "doi": "10.1016/j.oregeorev.2025.106798"},
    )


def modem_sample() -> InversionRecord:
    wd = paths.MODEM_SAMPLE
    f, comps, ns, sign, errs = _modem_data(wd / "27-freq-run-watex01.dat")
    ctrl = _modem_ctrl(wd / "inv.ctrl")
    rms, lam, it, stalled = _modem_log_tail(wd / "Modular_NLCG.log")
    return InversionRecord(
        solver="ModEM", solver_version="ModEM 3D MT, NLCG",
        data={"components": comps, "frequency_range_hz": [float(f"{f.min():.6g}"), float(f"{f.max():.6g}")],
              "n_frequencies": int(f.size), "n_stations": ns, "errors": errs,
              "sign_convention": sign, "source": "27-freq-run-watex01.dat"},
        forward={"dimensionality": "3D", "mesh": "41 x 50 x 288 cells"},
        regularization={"type": "ModEM model covariance (smoothing), NLCG",
                        "trade_off": lam, "start_model": "27-freq-run-watex01.rho"},
        misfit={"final_rms": rms,
                "target_rms": float(ctrl.get("Exit search when rms is less than", "nan")),
                "n_iterations": it, "termination": "stalled" if stalled else "unknown"},
    )


def mare2dem_demo(result) -> InversionRecord:
    wd = paths.MARE2DEM
    txt = (wd / "demo_mt_synth_static.emdata").read_text().splitlines()
    i = next(k for k, l in enumerate(txt) if l.startswith("# MT Frequencies"))
    nf = int(txt[i].split(":")[1])
    f = np.array([float(txt[i + 1 + k]) for k in range(nf)])
    nrx = int(next(l for l in txt if l.startswith("# MT Receivers")).split(":")[1])
    j = next(k for k, l in enumerate(txt) if l.startswith("# Data:"))
    types = sorted({int(l.split()[0]) for l in txt[j + 1:] if l.strip() and not l.startswith("!")})
    names = {123: "log10 rho Zxy", 104: "phase Zxy", 125: "log10 rho Zyx", 106: "phase Zyx"}
    hdr = (wd / result.model_files[-1].name).read_text().splitlines()

    def h(k):
        return next(l.split(":", 1)[1].strip() for l in hdr if l.strip().startswith(k))
    return InversionRecord(
        solver="MARE2DEM", solver_version=h("Format"),
        data={"components": [names.get(t, str(t)) for t in types],
              "frequency_range_hz": [float(f"{f.min():.6g}"), float(f"{f.max():.6g}")],
              "n_frequencies": nf, "n_stations": nrx,
              "errors": "as stated per datum in the data file",
              "source": "demo_mt_synth_static.emdata (synthetic MT data with static shifts)"},
        forward={"dimensionality": "2D (finite-element, adaptive mesh)"},
        regularization={"type": f"{h('Roughness Penalty Method')} roughness, "
                                f"weights (y,z) {h('Roughness Weights (y,z)')}, "
                                f"bounds {h('Global Bounds')} ohm m",
                        "trade_off": 10 ** float(h("Log10 Lagrange Value"))},
        misfit={"final_rms": float(h("Model Misfit")), "target_rms": float(h("Target Misfit")),
                "n_iterations": int(result.model_files[-1].name.split(".")[1]),
                "termination": "target_reached"},
    )


def synthetic(kind: str) -> InversionRecord:
    return InversionRecord(
        solver=f"synthetic {kind} prediction (format test, no trained network)",
        data={"source": "seeded synthetic array"})
