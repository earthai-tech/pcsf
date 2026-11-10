"""Package the source code for the GEOPHYSICS submission (author tool).

GEOPHYSICS papers in the "Geophysical Software and Algorithms"
section must come with well-documented ASCII source code uploaded
with the submission (links to external repositories are not
sufficient), without binary files other than data the code reads,
and with code that emphasises the algorithm rather than a user
interface (instructions to authors, read 2026-11-10).

This script writes ``paper/pcsf-seg-code-<version>.zip`` with:

- ``src/pcsf`` without the graphical viewer (``studio``);
- ``tests`` (without the viewer's tests), ``spec``, ``conformance``;
- ``paper`` (scripts, runners, expected results, README);
- ``pyproject.toml``, ``README.md``, ``LICENSE``, ``CHANGELOG.md``
  and a ``README_SEG.txt`` describing the package.

Binary files are refused, except the conformance and data files the
code reads (``.pcsf``, ``.gz``). The data archive itself is
deposited separately (``tools/make_data_archive.py``).

    python paper/tools/make_seg_code_package.py
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"

INCLUDE = ["src/pcsf", "tests", "spec", "conformance", "paper"]
FILES = ["pyproject.toml", "README.md", "LICENSE", "CHANGELOG.md"]
EXCLUDE_PARTS = {
    "__pycache__", ".pytest_cache", "studio", "data", "output",
    "dist", "build",
}
EXCLUDE_NAMES = {"sources.local.json"}
#: Binary data the code reads, allowed by the instructions.
DATA_SUFFIXES = {".pcsf", ".gz"}

README_SEG = """\
pcsf: reference implementation of the Portable Common Subsurface
Format (PCSF), source code accompanying the GEOPHYSICS manuscript.

Contents
  src/pcsf/      the package: data model, HDF5 and text encodings,
                 conformance rules, native parsers and adapters
                 (Occam2D, ModEM, MARE2DEM, EMC), sampling,
                 comparison, uncertainty and registration algorithms
  tests/         unit tests and doctests (pytest)
  spec/          specification of the format
  conformance/   reference files, expected checksums and runner
  paper/         scripts that reproduce every number, table and
                 figure of the manuscript (see paper/README.md)

Install and test (Python 3.9 or newer):
  pip install -e ".[algorithms,emc,mare2dem,geo,schema]" pytest
  pytest

Reproduce the manuscript:
  pip install -r paper/requirements.txt
  python paper/fetch_data.py        (data archive, see paper/)
  python paper/run_all.py
  python paper/check_results.py

The graphical viewer of the full distribution is not included: it
is not part of the algorithms described in the manuscript.
Licence: BSD 3-Clause (LICENSE).
"""


def is_binary(path: Path) -> bool:
    with path.open("rb") as fh:
        return b"\0" in fh.read(8192)


def collect() -> list[Path]:
    files = [ROOT / f for f in FILES]
    for top in INCLUDE:
        for p in sorted((ROOT / top).rglob("*")):
            rel = p.relative_to(ROOT)
            if not p.is_file() or EXCLUDE_PARTS & set(rel.parts[:-1]):
                continue
            if p.name in EXCLUDE_NAMES or p.suffix == ".zip":
                continue
            if rel.parts[:2] == ("tests", "studio"):
                continue
            files.append(p)
    return files


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--version", default="0.1.0")
    args = p.parse_args()
    files = collect()
    binary = [f for f in files
              if is_binary(f) and f.suffix not in DATA_SUFFIXES]
    if binary:
        listing = "\n".join(str(f.relative_to(ROOT)) for f in binary)
        raise SystemExit(f"binary files would be included:\n{listing}")
    out = PAPER / f"pcsf-seg-code-{args.version}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pcsf/README_SEG.txt", README_SEG)
        for f in files:
            zf.write(f, f"pcsf/{f.relative_to(ROOT).as_posix()}")
    size = out.stat().st_size / 1e6
    print(f"{out.name}: {len(files) + 1} files, {size:.2f} MB")


if __name__ == "__main__":
    main()
