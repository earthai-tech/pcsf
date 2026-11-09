"""Write the tiny synthetic solver runs in ``pcsf/datasets``.

The runs are small enough to read in a docstring example yet use
every feature the parsers handle: padding and an air row in the
Occam2D mesh, merged blocks in the Occam2D model, an origin trailer
and air fill in the ModEM model, a depth-down station column, and a
MARE2DEM table with a fixed air region. Values are deterministic.

Run from the repository root::

    python tools/make_tiny_datasets.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "pcsf" / "datasets"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def occam2d() -> None:
    d = OUT / "occam2d_tiny"
    xw = [200.0, 100.0, 50.0, 50.0, 50.0, 50.0, 100.0, 200.0]
    zw = [1000.0, 10.0, 20.0, 40.0]
    rows = ["0" * 8] * 4 + ["?" * 8] * 12
    _write(
        d / "Occam2DMesh",
        "MESH tiny\n0 9 5 0 0 2\n"
        + " ".join(f"{w:.1f}" for w in xw)
        + "\n"
        + " ".join(f"{w:.1f}" for w in zw)
        + "\n0\n"
        + "\n".join(rows)
        + "\n",
    )
    layers = [(1, [2, 2, 2, 2]), (1, [4, 4]), (1, [8])]
    body = "".join(
        f"{n} {len(c)}\n" + " ".join(map(str, c)) + "\n"
        for n, c in layers
    )
    _write(
        d / "Occam2DModel",
        "Format: OCCAM2MTMOD_1.0\nModel Name: tiny\n"
        "Mesh File: Occam2DMesh\nMesh Type: PW2D\n"
        f"Num Layers: {len(layers)}\n" + body,
    )
    _write(
        d / "OccamDataFile.dat",
        "FORMAT: OCCAM2MTDATA_1.0\nTITLE: tiny\nSITES: 3\n"
        "S01\nS02\nS03\nOFFSETS (M): 3\n0.0\n50.0\n100.0\n"
        "FREQUENCIES: 1\n10.0\nDATA BLOCKS: 0\n",
    )
    values = [[2.0, 2.2, 1.5, 2.4, 1.8, 2.6, 3.0]]
    values.append([2.1, 2.3, 1.4, 2.5, 1.9, 2.7, 3.1])
    for k, vals in enumerate(values, start=1):
        _write(
            d / f"ITER{k:02d}.iter",
            "Format: OCCAMITER_FLEX\nDescription: tiny\n"
            "Model File: Occam2DModel\nData File: OccamDataFile.dat\n"
            f"Iteration: {k}\nLagrange Value: {2.0 / k}\n"
            f"Roughness Value: {10.0 * k}\n"
            f"Misfit Value: {3.0 / k}\nMisfit Reached: 0\n"
            f"Param Count: {len(vals)}\n"
            + " ".join(f"{v:.6f}" for v in vals)
            + "\n",
        )
    _write(
        d / "LogFile.logfile",
        "".join(
            f" ** ITERATION {k} **\n"
            f" MINIMUM TOL FROM fminocc IS AT MU = {2.0 / k}\n"
            f" AND IS = {3.0 / k}\n STEPSIZE IS = 0.5\n"
            f" ROUGHNESS IS = {10.0 * k}\n"
            for k in (1, 2)
        ),
    )


def modem() -> None:
    d = OUT / "modem_tiny"
    nx, ny, nz = 5, 4, 3
    xw = [100.0, 50.0, 50.0, 50.0, 100.0]
    yw = [100.0, 50.0, 50.0, 100.0]
    zw = [10.0, 20.0, 40.0]
    rng = np.random.default_rng(7)
    ln_rho = np.log(10.0) * rng.uniform(1.0, 3.0, (nz, ny, nx))
    ln_rho[0, 0, :2] = np.log(1e12)  # air fill in one corner
    lines = ["# tiny ModEM model", f"{nx} {ny} {nz} 0 LOGE"]
    for w in (xw, yw, zw):
        lines.append(" ".join(f"{v:.3f}" for v in w))
    for k in range(nz):
        for j in range(ny):
            # WS order: x from north (last index) to south.
            lines.append(
                " ".join(f"{v:.8e}" for v in ln_rho[k, j, ::-1])
            )
    lines += ["-175.000 -150.000 0.000", "0.0"]
    _write(d / "tiny_NLCG_002.rho", "\n".join(lines) + "\n")
    head = (
        "# tiny data; Z is depth below 300 m a.s.l.\n"
        "# Period(s) Code GG_Lat GG_Lon X(m) Y(m) Z(m) "
        "Component Real Imag Error\n"
        "> Off_Diagonal_Impedance\n> exp(+i\\omega t)\n"
        "> [mV/km]/[nT]\n> 0.00\n> 0.000 0.000\n> 1 2\n"
    )
    rows = []
    for code, lat, lon, x, y, z in (
        ("A01", 25.12345, 117.54321, -25.0, -50.0, 5.0),
        ("A02", 25.12445, 117.54421, 25.0, 50.0, 12.0),
    ):
        for comp in ("ZXY", "ZYX"):
            rows.append(
                f"1.0000E-01 {code} {lat:.5f} {lon:.5f} {x:.3f} "
                f"{y:.3f} {z:.3f} {comp} 1.0 -1.0 0.1"
            )
    _write(d / "tiny.dat", head + "\n".join(rows) + "\n")
    vals = "f= {f:.5E} m2= {m:.5E} rms= {r:.6f} lambda= 1.00000E+01 "
    vals += "alpha= 2.00000E+01"
    log = " START: " + vals.format(f=90.0, m=0.0, r=9.5) + "\n"
    for k, r in ((1, 4.2), (2, 1.9)):
        log += f" Completed NLCG iteration {k}\n"
        log += "     with: " + vals.format(f=9 * r, m=0.1 * k, r=r)
        log += "\n"
    _write(d / "tiny_NLCG.log", log)


def mare2dem() -> None:
    d = OUT / "mare2dem_tiny"
    nodes = np.array(
        [
            [0.0, -50.0],
            [100.0, -50.0],
            [0.0, 0.0],
            [100.0, 0.0],
            [0.0, 50.0],
            [100.0, 50.0],
        ]
    )
    # Two air triangles (region 1), two earth triangles (region 2).
    tri = np.array([[0, 1, 3], [0, 3, 2], [2, 3, 5], [2, 5, 4]])
    region = np.array([1, 1, 2, 2])
    d.mkdir(parents=True, exist_ok=True)
    np.savetxt(d / "tiny.node.txt", nodes, fmt="%.1f")
    np.savetxt(
        d / "tiny.ele.txt", np.column_stack([tri, region]), fmt="%d"
    )
    _write(
        d / "tiny.1.resistivity",
        " Format:              MARE2DEM_1.1\n"
        " Model File:          tiny.poly\n"
        " Model Misfit:        1.05\n"
        " Anisotropy:          isotropic\n"
        " Number of regions:   2\n"
        "!#  Rho  Param  Lower  Upper  Prej  Weight\n"
        "  1  1.0000E+12  0  0  0  0  0\n"
        "  2  4.5000E+01  1  0  0  0  0\n",
    )
    poly = ["6 2 0 0"]
    poly += [
        f"{i + 1} {x:.1f} {z:.1f}" for i, (x, z) in enumerate(nodes)
    ]
    segs = [(1, 2), (2, 4), (4, 6), (6, 5), (5, 3), (3, 1), (3, 4)]
    poly.append(f"{len(segs)} 0")
    poly += [f"{k + 1} {a} {b}" for k, (a, b) in enumerate(segs)]
    poly += ["0", "2", "1 50.0 -25.0 1 -1", "2 50.0 25.0 2 -1"]
    _write(d / "tiny.poly", "\n".join(poly) + "\n")
    _write(
        d / "tiny.logfile",
        "** Iteration     1 **\n Model Misfit:        3.2\n"
        " Roughness:           0.8\n Optimal Mu:          2.0\n"
        " Convergence Status:  0\n"
        "** Iteration     2 **\n Model Misfit:        1.05\n"
        " Roughness:           1.1\n Optimal Mu:          1.5\n"
        " Convergence Status:  1\n",
    )


if __name__ == "__main__":
    occam2d()
    modem()
    mare2dem()
