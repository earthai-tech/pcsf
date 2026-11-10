"""Assemble the data archive of the paper (author tool).

Copies, from the authors' working copies, exactly the files the
reproduction reads into ``paper/data/``, writes ``SHA256SUMS`` and
packs ``pcsf-paper-data-<version>.zip`` for the Zenodo record.
Reviewers do not run this; they download the archive with
``fetch_data.py``.

Layout of ``paper/data/``:

==================================  ==================================
``models/``                         converted models (.pcsf, .pcsm)
``native/occam2d/tongkeng/``        Occam2D run, Tongkeng CSAMT line
``native/occam2d/baohuashan/LxxPLT``  Occam2D runs, Baohuashan lines
``native/modem/baohuashan/``        ModEM 3D model, Baohuashan survey
``native/modem/sample/``            ModEM 3D sample run
``native/mare2dem/demo/``           MARE2DEM demonstration inversion
``native/emc/``                     EMC netCDF files and solver models
``edi/baohuashan/LxxPLT/``          processed EDI files, L18 and L22
``tables/``                         run summary of the Occam2D lines
``rebuild/``                        other inputs of the rebuild
==================================  ==================================

Of the Baohuashan survey, only lines L18 and L22 are public. For
the other lines (L26, L30, L34) the archive holds the inversion
models but no measured data: their EDI files, the Occam2D data file
and final response, and the data files of the two ModEM runs (which
hold all stations of the survey) are left out and listed in
``RESTRICTED.txt``. They are available from the authors on
reasonable request.

The source folders are read from ``tools/sources.local.json`` (not
in git), with keys ``pycsamt`` (pyCSAMT checkout), ``runs`` (Occam2D
and ModEM run folders) and ``modem_field`` (full ModEM output of the
Baohuashan run)::

    python paper/tools/make_data_archive.py --version 1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
DATA = PAPER / "data"
_LOCAL = Path(__file__).with_name("sources.local.json")
if not _LOCAL.exists():
    raise SystemExit(f"{_LOCAL} not found (see the module docstring)")
_SRC = json.loads(_LOCAL.read_text(encoding="utf-8"))
PYCSAMT = Path(_SRC["pycsamt"])
GEOPHYSICS = PYCSAMT / "PAPERS/GEOPHYSICS"
RUNS = Path(_SRC["runs"])
MODEM_FIELD = Path(_SRC["modem_field"])
LINES = ("L18", "L22", "L26", "L30", "L34")
#: Baohuashan lines whose measured data may be published.
PUBLIC_LINES = ("L18", "L22")
#: Occam2D files that hold measured data (data file, responses).
OCCAM_DATA = ("OccamDataFile.dat",)
#: ModEM data file of the Baohuashan 3D inversion (all stations).
MODEM_DATA = "ModEMData_v5_offdiag.dat"
#: ModEM data file of the 27-frequency sample run (125 stations).
MODEM_SAMPLE_DATA = "27-freq-run-watex01.dat"
#: Files withheld from the archive, written to RESTRICTED.txt.
RESTRICTED: list[str] = []
RESTRICTED_HEADER = (
    "Files of the Baohuashan survey withheld from this archive.\n"
    "Only lines L18 and L22 of the survey are public; the inversion\n"
    "models of all lines are included. The files below hold measured\n"
    "data of lines L26, L30 and L34 (the two ModEM data files hold\n"
    "all stations of the survey) and are available from the authors\n"
    "on reasonable request.\n\n"
)
#: README of the archive (also the Zenodo description source).
README = Path(__file__).with_name("data_archive_README.md")


def occam_files(run: Path, data: bool = True) -> list[Path]:
    """Inputs of an Occam2D run and its final response.

    Every ``ITER*.iter`` file is kept (the record of the run's
    iterations); of the responses only the last; console logs, which
    reach hundreds of MB, are left out. With ``data=False`` the data
    file and the response, which hold measured data, are left out
    too.
    """
    keep = [
        p
        for p in sorted(run.iterdir())
        if p.is_file()
        and (
            p.suffix == ".iter"
            or p.name
            in (
                "Occam2DMesh",
                "Occam2DModel",
                "OccamDataFile.dat",
                "Startup",
                "LogFile.logfile",
                "occam2d.yml",
            )
        )
    ]
    resp = sorted(run.glob("RESP*.resp"))[-1:]
    if not data:
        keep = [p for p in keep if p.name not in OCCAM_DATA]
        resp = []
    return keep + resp


def plan() -> list[tuple[Path, Path]]:
    """``(source, destination relative to data/)`` of every file."""
    out: list[tuple[Path, Path]] = []

    def add(src: Path, dst: str) -> None:
        out.append((src, Path(dst)))

    # The models are those of the rebuild from the native runs
    # (run_all.py --rebuild), so that the archive holds what tier 2
    # reproduces.
    rebuilt = PAPER / "output" / "models"
    models = sorted(rebuilt.glob("*.pcs[fm]"))
    if not models:
        raise SystemExit(f"no models in {rebuilt}; run run_all.py --rebuild")
    for p in models:
        add(p, f"models/{p.name}")
    for p in occam_files(PYCSAMT / "data/occam2D"):
        add(p, f"native/occam2d/tongkeng/{p.name}")
    for line in LINES:
        run = RUNS / "occam2d" / f"{line}PLT"
        public = line in PUBLIC_LINES
        for p in occam_files(run, data=public):
            add(p, f"native/occam2d/baohuashan/{line}PLT/{p.name}")
        if not public:
            kept = set(occam_files(run, data=False))
            RESTRICTED.extend(
                f"native/occam2d/baohuashan/{line}PLT/{p.name}"
                for p in occam_files(run) if p not in kept)
    src = RUNS / "student_modem3d_pcsf_src"
    for name in ("stageA_v5_NLCG_113.rho", "stageA_v5_NLCG.log"):
        add(src / name, f"native/modem/baohuashan/{name}")
    RESTRICTED.append(f"native/modem/baohuashan/{MODEM_DATA}")
    add(MODEM_FIELD / "stageA_v5.inv",
        "native/modem/baohuashan/stageA_v5.inv")
    add(src / "student_baohuashan_modem3d.pcsf",
        "rebuild/modem_baohuashan_stations.pcsf")
    sample = PYCSAMT / "data/modem/willy_27freq_watex_line02_sample"
    for name in ("Modular_NLCG_073.rho", "Modular_NLCG.log",
                 "inv.ctrl"):
        add(sample / name, f"native/modem/sample/{name}")
    # The sample run inverts the full impedance of all five lines.
    RESTRICTED.append(f"native/modem/sample/{MODEM_SAMPLE_DATA}")
    add(PYCSAMT / "examples/pcsf_conversion_demo/output/"
        "modem3d_with_topo.pcsf", "rebuild/modem_sample_stations.pcsf")
    demo = PYCSAMT / "data/mare2dem/demo_mt_inversion"
    for p in sorted(demo.iterdir()):
        if p.is_file():
            add(p, f"native/mare2dem/demo/{p.name}")
    emc = GEOPHYSICS / "data/emc_raw"
    for nc in sorted(emc.glob("*.nc")):
        add(nc, f"native/emc/{nc.name}")
    for folder in sorted(p for p in emc.iterdir() if p.is_dir()):
        for p in sorted(folder.iterdir()):
            add(p, f"native/emc/{folder.name}/{p.name}")
    edi = PYCSAMT / "PAPERS/PAGEO/data/processed_edi"
    for line in LINES:
        for p in sorted((edi / f"{line}PLT").glob("*.edi")):
            rel = f"edi/baohuashan/{line}PLT/{p.name}"
            if line in PUBLIC_LINES:
                add(p, rel)
            else:
                RESTRICTED.append(rel)
    add(PYCSAMT / "PAPERS/PAGEO/results/occam2d_run_summary.csv",
        "tables/occam2d_run_summary.csv")
    ex = PYCSAMT / "examples"
    add(ex / "pcsf_conversion_demo/output/occam2d_with_topo.pcsf",
        "rebuild/tongkeng_occam2d_with_topo.pcsf")
    add(ex / "ai_inversion_pcsf/output/toy_unet_grid2d.pcsf",
        "rebuild/synthetic_unet.pcsf")
    add(ex / "ai_inversion_pcsf/output/toy_gcn_mesh.pcsf",
        "rebuild/synthetic_gcn.pcsf")
    add(PYCSAMT / "data/avg/k1.stn", "rebuild/tongkeng_k1.stn")
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--version", default="1", help="archive version")
    p.add_argument("--no-zip", action="store_true")
    args = p.parse_args()
    files = plan()
    missing = [s for s, _ in files if not s.is_file()]
    if missing:
        listing = "\n".join(map(str, missing))
        raise SystemExit(f"missing sources:\n{listing}")
    keep = {".gitignore"}
    for old in DATA.iterdir() if DATA.exists() else []:
        if old.name not in keep:
            shutil.rmtree(old) if old.is_dir() else old.unlink()
    lines = []
    for src, rel in files:
        dst = DATA / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        lines.append(f"{sha256(dst)}  {rel.as_posix()}")
    (DATA / "SHA256SUMS").write_text("\n".join(lines) + "\n",
                                     encoding="utf-8")
    shutil.copyfile(README, DATA / "README.md")
    (DATA / "RESTRICTED.txt").write_text(
        RESTRICTED_HEADER + "\n".join(RESTRICTED) + "\n",
        encoding="utf-8")
    size = sum((DATA / r).stat().st_size for _, r in files)
    print(f"{len(files)} files, {size / 1e6:.1f} MB in {DATA}")
    if args.no_zip:
        return
    archive = PAPER / f"pcsf-paper-data-{args.version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("README.md", "SHA256SUMS", "RESTRICTED.txt"):
            zf.write(DATA / name, f"data/{name}")
        for _, rel in files:
            zf.write(DATA / rel, f"data/{rel.as_posix()}")
    print(f"{archive.name}: {archive.stat().st_size / 1e6:.1f} MB, "
          f"sha256 {sha256(archive)}")


if __name__ == "__main__":
    main()
