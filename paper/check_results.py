"""Compare a reproduction run with the results reported in the paper.

Every table in ``expected/`` (the values in the manuscript) is
compared with the same table in ``output/results``: numbers with a
relative tolerance, text exactly. Timing columns (``*_s``) depend on
the computer and are not compared. Tables written only by the
rebuild (tier 2) are reported as not run when they are absent.

    python paper/check_results.py [--rtol 1e-6]

The exit status is 0 when every compared value agrees.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parent
EXPECTED = PAPER / "expected"
sys.path.insert(0, str(PAPER / "scripts"))
import paths  # noqa: E402

#: Tables written by the rebuild only (run_all.py --rebuild).
TIER2 = {
    "field_models.csv",
    "inversion_records.csv",
    "modem_orientation.csv",
    "depth_of_investigation.json",
}
#: Columns that hold the size of a file whose bytes include the
#: library version or a time stamp; compared with a looser tolerance.
SIZE_COLUMNS = ("_bytes", "_mb")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _same(a, b, rtol: float) -> bool:
    x, y = _num(a), _num(b)
    if x is None or y is None:
        return str(a) == str(b)
    if math.isnan(x) and math.isnan(y):
        return True
    return abs(x - y) <= rtol * max(1.0, abs(x), abs(y))


def _flat(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flat(v, f"{prefix}{k}.")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _flat(v, f"{prefix}{i}.")
    else:
        yield prefix.rstrip("."), obj


def _rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    key = next(iter(rows[0])) if rows else ""
    return {f"{i}:{r[key]}" if list(r).count(key) else str(i): r
            for i, r in enumerate(rows)}


def compare(old: Path, new: Path, rtol: float) -> list[str]:
    diffs = []
    if old.suffix == ".json":
        a = dict(_flat(json.loads(old.read_text(encoding="utf-8"))))
        b = dict(_flat(json.loads(new.read_text(encoding="utf-8"))))
        for k, v in a.items():
            if k not in b:
                diffs.append(f"{k}: missing")
            elif not _same(v, b[k], rtol):
                diffs.append(f"{k}: {v} -> {b[k]}")
        return diffs
    a, b = _rows(old), _rows(new)
    if len(a) != len(b):
        diffs.append(f"rows {len(a)} -> {len(b)}")
    for (ka, ra), rb in zip(a.items(), b.values()):
        for col, v in ra.items():
            if col.endswith("_s"):
                continue
            tol = 0.01 if col.endswith(SIZE_COLUMNS) else rtol
            if col not in rb:
                diffs.append(f"[{ka}] {col}: missing")
            elif not _same(v, rb[col], tol):
                diffs.append(f"[{ka}] {col}: {v} -> {rb[col]}")
    return diffs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rtol", type=float, default=1e-6,
                   help="relative tolerance of numbers (default 1e-6)")
    args = p.parse_args(argv)
    failed = 0
    for old in sorted(EXPECTED.iterdir()):
        new = paths.RESULTS / old.name
        if not new.exists():
            status = ("not run (tier 2)" if old.name in TIER2
                      else "MISSING")
            failed += status == "MISSING"
            print(f"{old.name:32s} {status}")
            continue
        diffs = compare(old, new, args.rtol)
        failed += bool(diffs)
        verdict = f"{len(diffs)} differences" if diffs else "agrees"
        print(f"{old.name:32s} {verdict}")
        for d in diffs[:20]:
            print(f"    {d}")
    print("all compared values agree" if not failed
          else f"{failed} table(s) differ")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
