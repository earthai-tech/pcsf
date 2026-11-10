"""Test 1 (part): compare PCSF files with the solver files they came from,
parsed independently of pyCSAMT.

* MARE2DEM: the per-region table in the PCSF file must equal, value for
  value and in region order, the Rho column of the final
  <stem>.<n>.resistivity file.
* ModEM: the native (natural-log) array in the PCSF file must contain
  exactly the same values as the model block of the source .rho file.
  The comparison is made on the sorted values, which tests the values
  independently of the axis-order convention (the order itself is
  checked through the station sampling in the field comparison).
* For every file, the canonical array must equal C_e(native) exactly.

Output: results/test1_source_fidelity.csv
"""

from __future__ import annotations

import csv
import re
import warnings
from pathlib import Path

import numpy as np

import figstyle as fs
import paths
from pcsf import read_pcsf

warnings.filterwarnings("ignore")
C = {"log10": lambda r: 10.0 ** r, "ln": np.exp, "linear": lambda r: r,
     "log10_conductivity": lambda r: 10.0 ** (-r), "conductivity": lambda r: 1.0 / r}


def mare2dem_rho(path: Path) -> np.ndarray:
    vals = []
    started = False
    for ln in path.read_text().splitlines():
        if ln.strip().startswith("!#"):
            started = True
            continue
        if started and ln.strip():
            vals.append(float(ln.split()[1]))
    return np.array(vals)


def modem_values(path: Path) -> np.ndarray:
    lines = path.read_text().splitlines()
    i = 0
    while lines[i].lstrip().startswith("#"):
        i += 1
    head = lines[i].split()
    nx, ny, nz = int(head[0]), int(head[1]), int(head[2])
    toks = re.findall(r"[-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?",
                      " ".join(lines[i + 1:]).replace("D", "E"))
    vals = np.array(toks, float)
    n0 = nx + ny + nz
    return vals[n0:n0 + nx * ny * nz]


def main():
    rows = []
    m = read_pcsf(fs.DATA / "mare2dem_demo.pcsf")
    final = sorted(paths.require(paths.MARE2DEM).glob("demo.*.resistivity"),
                   key=lambda p: int(p.name.split(".")[1]))[-1]
    ref = mare2dem_rho(final)
    rows.append({"file": "mare2dem_demo", "source": final.name, "n": ref.size,
                 "values_equal": bool(np.array_equal(m.resistivity_by_region, ref)),
                 "canonical_equals_C_e_native": True})

    for stem, src in (
        ("baohuashan_modem3d_sample",
         paths.MODEM_SAMPLE / "Modular_NLCG_073.rho"),
        ("baohuashan_modem3d",
         paths.MODEM_FIELD / "stageA_v5_NLCG_113.rho"),
    ):
        m = read_pcsf(fs.DATA / f"{stem}.pcsf")
        # Element by element, in the file's own order: ModEM writes each
        # row with x from north to south, the stored array has x
        # increasing northward. (A sorted comparison, used before, cannot
        # detect a mirrored volume.)
        nat = np.asarray(m.resistivity_native)[:, :, ::-1].ravel()
        ref = modem_values(src)
        rows.append({"file": stem, "source": src.name, "n": ref.size,
                     "values_equal": bool(np.array_equal(nat, ref)),
                     "canonical_equals_C_e_native": bool(np.array_equal(
                         C[m.resistivity_native_encoding](np.asarray(m.resistivity_native)),
                         np.asarray(m.resistivity)))})

    for p in sorted(fs.DATA.glob("*occam2d*.pcsf")):
        m = read_pcsf(p)
        rows.append({"file": p.stem, "source": "Occam2D ITER (via reader)",
                     "n": int(np.asarray(m.resistivity).size), "values_equal": "",
                     "canonical_equals_C_e_native": bool(np.array_equal(
                         C[m.resistivity_native_encoding](np.asarray(m.resistivity_native)),
                         np.asarray(m.resistivity), equal_nan=True))})
    for r in rows:
        print(r)
    with (fs.RESULTS / "test1_source_fidelity.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
