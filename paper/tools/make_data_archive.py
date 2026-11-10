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
``native/modem/baohuashan/``        ModEM 3D run, Baohuashan survey
``native/modem/sample/``            ModEM 3D sample run
``native/mare2dem/demo/``           MARE2DEM demonstration inversion
``native/emc/``                     EMC netCDF files and solver models
``edi/baohuashan/LxxPLT/``          processed EDI files (rebuild)
``tables/``                         run summary of the Occam2D lines
``rebuild/``                        other inputs of the rebuild
==================================  ==================================

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


def occam_files(run: Path) -> list[Path]:
    """Inputs of an Occam2D run and its final response.

    Every ``ITER*.iter`` file is kept (the record of the run's
    iterations); of the responses only the last; console logs, which
    reach hundreds of MB, are left out.
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
    resp = sorted(run.glob("RESP*.resp"))
    return keep + resp[-1:]


def plan() -> list[tuple[Path, Path]]:
    """``(source, destination relative to data/)`` of every file."""
    out: list[tuple[Path, Path]] = []

    def add(src: Path, dst: str) -> None:
        out.append((src, Path(dst)))

    for p in sorted((GEOPHYSICS / "data").glob("*.pcs[fm]")):
        add(p, f"models/{p.name}")
    for p in occam_files(PYCSAMT / "data/occam2D"):
        add(p, f"native/occam2d/tongkeng/{p.name}")
    for line in LINES:
        for p in occam_files(RUNS / "occam2d" / f"{line}PLT"):
            add(p, f"native/occam2d/baohuashan/{line}PLT/{p.name}")
    src = RUNS / "student_modem3d_pcsf_src"
    for name in ("stageA_v5_NLCG_113.rho", "stageA_v5_NLCG.log",
                 "ModEMData_v5_offdiag.dat"):
        add(src / name, f"native/modem/baohuashan/{name}")
    add(MODEM_FIELD / "stageA_v5.inv",
        "native/modem/baohuashan/stageA_v5.inv")
    add(src / "student_baohuashan_modem3d.pcsf",
        "rebuild/modem_baohuashan_stations.pcsf")
    sample = PYCSAMT / "data/modem/willy_27freq_watex_line02_sample"
    for name in ("Modular_NLCG_073.rho", "Modular_NLCG.log",
                 "27-freq-run-watex01.dat", "inv.ctrl"):
        add(sample / name, f"native/modem/sample/{name}")
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
            add(p, f"edi/baohuashan/{line}PLT/{p.name}")
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
    keep = {"README.md", ".gitignore"}
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
    size = sum((DATA / r).stat().st_size for _, r in files)
    print(f"{len(files)} files, {size / 1e6:.1f} MB in {DATA}")
    if args.no_zip:
        return
    archive = PAPER / f"pcsf-paper-data-{args.version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(DATA / "SHA256SUMS", "data/SHA256SUMS")
        for _, rel in files:
            zf.write(DATA / rel, f"data/{rel.as_posix()}")
    print(f"{archive.name}: {archive.stat().st_size / 1e6:.1f} MB, "
          f"sha256 {sha256(archive)}")


if __name__ == "__main__":
    main()
