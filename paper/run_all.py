"""Reproduce every number, table and figure of the paper.

Tier 1 (default) needs pcsf and the data archive only: the analyses
read the archived models in ``data/models`` and the native files in
``data/native``. Tier 2 (``--rebuild``) first rebuilds the models
from the native runs and EDI files, which also needs pyCSAMT, writes
them to ``output/models`` and runs the analyses on those.

    python paper/fetch_data.py          # once
    python paper/run_all.py             # tier 1
    python paper/run_all.py --rebuild   # tier 2, then tier 1
    python paper/check_results.py       # compare with expected/

Outputs: ``output/results`` (tables) and ``output/figures``.
"""

from __future__ import annotations

import argparse
import os
import runpy
import sys
import time
from pathlib import Path

PAPER = Path(__file__).resolve().parent
SCRIPTS = PAPER / "scripts"

#: Tier 1, in order: (script, what it writes).
ANALYSES = [
    ("test1_source_fidelity.py", "results/test1_source_fidelity.csv"),
    ("test2_sampling_accuracy.py",
     "results/test2_*.csv, figures/test2_sampling"),
    ("test3_independent_readers.py",
     "results/test3_independent_readers.csv"),
    ("test4_storage_benchmark.py",
     "results/test4_storage.csv, figures/test4_storage"),
    ("ambiguities.py", "results/ambiguities.csv"),
    ("field_2d_vs_3d.py",
     "results/field_2d3d_*, figures/field_2d3d_*"),
    ("frames_uncertainty.py",
     "results/frames_registration.json, uncertainty_delta.csv"),
    ("emc_roundtrip.py", "results/emc_*.csv, figures/emc_vs_solver"),
    ("field_figures.py",
     "figures/field_tongkeng, field_mare2dem, field_baohuashan"),
    ("make_schematics.py",
     "figures/datachain, datamodel, architecture"),
]
#: Tier 2: rebuild of the models (needs pyCSAMT).
REBUILD = [("build_field_models.py", "models/*.pcsf, *.pcsm")]


def run(script: str) -> float:
    t0 = time.perf_counter()
    print(f"=== {script}", flush=True)
    runpy.run_path(str(SCRIPTS / script), run_name="__main__")
    dt = time.perf_counter() - t0
    print(f"=== {script} done in {dt:.1f} s\n", flush=True)
    return dt


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rebuild", action="store_true",
                   help="rebuild the models first (needs pyCSAMT)")
    p.add_argument("--only", nargs="+", metavar="SCRIPT",
                   help="run only these scripts")
    args = p.parse_args(argv)
    sys.path.insert(0, str(SCRIPTS))
    import paths

    steps = [s for s, _ in ANALYSES]
    if args.rebuild:
        models = paths.OUT / "models"
        models.mkdir(parents=True, exist_ok=True)
        os.environ["PCSF_PAPER_MODELS"] = str(models)
        paths.MODELS = models
        steps = [s for s, _ in REBUILD] + steps
    if args.only:
        steps = [s for s in steps if s in args.only]
    paths.require(paths.DATA / "SHA256SUMS")
    total = sum(run(s) for s in steps)
    print(f"done: {len(steps)} scripts in {total:.0f} s; outputs in "
          f"{paths.OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
