"""Checks behind the frame-transformation and uncertainty equations.

1. Decompose the affine registration fitted for the Baohuashan ModEM model
   (field_2d_vs_3d.registration) into an axis permutation P, a rotation
   R(theta) and scales: A = R(theta) S P. A north-first ModEM grid should
   give P = [[0, 1], [1, 0]] (easting and northing swapped), unit scales
   and a small rotation (grid north versus UTM grid north).
2. Accuracy of the first-order (delta-method) conversion of a log10
   standard deviation sigma_m to a linear standard deviation, against the
   exact standard deviation of a log-normal variable with the same median:
       delta:  sigma_rho / rho_med = ln(10) sigma_m
       exact:  sigma_rho / rho_med = sqrt((exp(s^2) - 1) exp(s^2)),  s = ln(10) sigma_m

Outputs: results/frames_registration.json, results/uncertainty_delta.csv
"""

from __future__ import annotations

import csv
import json
import warnings

import numpy as np

import figstyle as fs
from field_2d_vs_3d import registration
from pcsf import read_pcsf

warnings.filterwarnings("ignore")


def main():
    m3 = read_pcsf(fs.DATA / "baohuashan_modem3d.pcsf")
    _, _, reg = registration(m3)
    A = np.array([reg["coef_x"][:2], reg["coef_y"][:2]])   # rows: gx, gy; cols: E, N
    P = np.array([[0.0, 1.0], [1.0, 0.0]])
    B = A @ P            # = R(theta) S if the permutation is right
    U, s, Vt = np.linalg.svd(B)
    R = U @ Vt
    theta = float(np.degrees(np.arctan2(R[1, 0], R[0, 0])))
    out = {"A": A.tolist(), "det_A": float(np.linalg.det(A)),
           "singular_values": s.tolist(), "rotation_deg": theta,
           "rms_residual_m": reg["rms_residual_m"],
           "max_residual_m": reg["max_residual_m"]}
    (fs.RESULTS / "frames_registration.json").write_text(json.dumps(out, indent=2))
    print(out)

    rows = []
    for sm in (0.01, 0.05, 0.1, 0.2, 0.3, 0.5):
        s_ = np.log(10) * sm
        exact = np.sqrt((np.exp(s_ ** 2) - 1) * np.exp(s_ ** 2))
        delta = s_
        rows.append({"sigma_log10": sm, "delta_rel": round(delta, 5),
                     "exact_rel": round(float(exact), 5),
                     "delta_error_pct": round(100 * (delta - exact) / exact, 2)})
        print(rows[-1])
    with (fs.RESULTS / "uncertainty_delta.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
