"""Test 3: read every manuscript file without the reference implementation.

For each model file of the paper the canonical resistivity is read four ways:

  ref     pcsf.read_pcsf (reference implementation)
  h5py    indep_readers.read_pcsf_h5py (h5py only, written from the spec)
  h5dump  indep_readers.read_pcsf_h5dump (HDF5 C command-line tool)
  pcsm    indep_readers.read_pcsm_text applied to the .pcsm sibling

and each independent result is compared bit for bit with the reference.
The h5py reader also checks the conformance rules of the specification.

Output: results/test3_independent_readers.csv
"""

from __future__ import annotations

import csv
import warnings

import numpy as np

import figstyle as fs
import indep_readers as ir
from pcsf import read_pcsf

warnings.filterwarnings("ignore")


def reference_arrays(model):
    if model.kind == "multiline":
        return {l.line_id: np.asarray(l.resistivity) for l in model.geometry.lines}
    return {"model": np.asarray(model.resistivity)}


def dataset_path(kind, key):
    return f"/geometry/lines/{key}/resistivity" if kind == "multiline" else "/model/resistivity"


def main():
    rows = []
    for path in sorted(fs.DATA.glob("*.pcsf")):
        ref = reference_arrays(read_pcsf(path))
        h5 = ir.read_pcsf_h5py(path)
        doc = ir.read_pcsm_text(path.with_suffix(".pcsm"))
        txt = ir.pcsm_resistivity(doc)
        n_vals = 0
        eq = {"h5py": True, "h5dump": True, "pcsm": True}
        for k, a in ref.items():
            n_vals += a.size
            b = h5["arrays"][dataset_path(h5["kind"], k).lstrip("/")]
            eq["h5py"] &= bool(np.array_equal(a, b, equal_nan=True))
            c = ir.read_pcsf_h5dump(path, dataset_path(h5["kind"], k))
            eq["h5dump"] &= bool(np.array_equal(a.ravel(), c, equal_nan=True))
            eq["pcsm"] &= bool(np.array_equal(a, txt[k], equal_nan=True))
        checks = h5["checks"]
        rows.append({
            "file": path.stem, "kind": h5["kind"], "n_values": n_vals,
            "h5py_exact": eq["h5py"], "h5dump_exact": eq["h5dump"],
            "pcsm_exact": eq["pcsm"],
            "conformance_checks": len(checks),
            "conformance_passed": sum(bool(v) for v in checks.values()),
            "native_max_rel_diff": h5.get("max_rel_native", ""),
        })
        print(rows[-1])
    with (fs.RESULTS / "test3_independent_readers.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    total = sum(r["n_values"] for r in rows)
    ok = all(r["h5py_exact"] and r["h5dump_exact"] and r["pcsm_exact"] and
             r["conformance_checks"] == r["conformance_passed"] for r in rows)
    print(f"{len(rows)} files, {total} resistivity values, all exact and conformant: {ok}")


if __name__ == "__main__":
    main()
