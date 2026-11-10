"""Test 4: file size and input/output time of PCSF against alternatives.

For four models -- Tongkeng (grid2d), the Baohuashan five-line model
(multiline), the MARE2DEM demonstration (mesh) and the 590 400-cell
ModEM sample (grid3d) -- each representation is written and read back
N_REPEAT times; the median wall-clock time is reported.

Representations
  native   the solver's own model files (size only)
  PCSF     HDF5, reference implementation
  PCSM     plain text, reference implementation
  PCSM.gz  gzip-compressed text, reference implementation
  netCDF   netCDF-4 (zlib level 4) with coordinates and resistivity only,
           written with netCDF4-python as a typical user export
  VTK      legacy binary VTK (rectilinear or unstructured grid), with
           log10 resistivity as cell data, written by vtk_legacy below

netCDF and VTK files hold only the arrays a visualisation needs; they do
not carry encoding, provenance or station metadata, which is the point
of comparison in the manuscript.

Outputs: results/test4_storage.csv, Fig/test4_storage.{png,pdf}
"""

from __future__ import annotations

import csv
import statistics
import tempfile
import time
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import netCDF4
import numpy as np

import figstyle as fs
import paths
from pcsf import read_pcsf, read_pcsm, write_pcsf, write_pcsm

warnings.filterwarnings("ignore")
N_REPEAT = 5

MODELS = {
    "Tongkeng\n(grid2d)": ("tongkeng_occam2d",
                           [paths.TONGKENG / "Occam2DMesh", paths.TONGKENG / "Occam2DModel",
                            paths.TONGKENG / "ITER17.iter"]),
    "Baohuashan\n(multiline)": ("baohuashan_multiline",
                                sum(([paths.OCCAM_BAOHUASHAN / f"{l}PLT/Occam2DMesh",
                                      paths.OCCAM_BAOHUASHAN / f"{l}PLT/Occam2DModel"]
                                     for l in ("L18", "L22", "L26", "L30", "L34")), [])),
    "MARE2DEM\n(mesh)": ("mare2dem_demo",
                         [paths.MARE2DEM / "demo.6.resistivity",
                          paths.MARE2DEM / "demo.poly"]),
    "ModEM sample\n(grid3d)": ("baohuashan_modem3d_sample",
                               [paths.MODEM_SAMPLE / "Modular_NLCG_073.rho"]),
}


def native_size(files):
    """Size of the native model files; Occam2D ITER files are taken as the
    last iteration of each run."""
    total = 0
    for f in files:
        total += f.stat().st_size
    if any(paths.OCCAM_BAOHUASHAN in f.parents for f in files):
        for line in ("L18", "L22", "L26", "L30", "L34"):
            iters = sorted((paths.OCCAM_BAOHUASHAN / f"{line}PLT").glob("ITER*.iter"))
            total += iters[-1].stat().st_size
    return total


# ------------------------------------------------------------ netCDF
def write_netcdf(model, path):
    with netCDF4.Dataset(path, "w", format="NETCDF4") as nc:
        def put_grid(grp, geo, rho):
            if rho.ndim == 3:
                for n, v in (("z", geo.z), ("y", geo.y), ("x", geo.x)):
                    grp.createDimension(n, v.size)
                    grp.createVariable(n, "f8", (n,))[:] = v
                grp.createVariable("resistivity", "f8", ("z", "y", "x"),
                                   zlib=True, complevel=4)[:] = rho
            else:
                for n, v in (("z", geo.z), ("x", geo.x)):
                    grp.createDimension(n, v.size)
                    grp.createVariable(n, "f8", (n,))[:] = v
                grp.createVariable("resistivity", "f8", ("z", "x"),
                                   zlib=True, complevel=4)[:] = rho
        geo = model.geometry
        if model.kind == "multiline":
            for line in geo.lines:
                put_grid(nc.createGroup(line.line_id), line.geometry,
                         np.asarray(line.resistivity))
        elif model.kind == "mesh_unstructured":
            nc.createDimension("node", geo.nodes.shape[0])
            nc.createDimension("dim", geo.nodes.shape[1])
            nc.createDimension("cell", geo.connectivity.shape[0])
            nc.createDimension("vertex", 3)
            nc.createVariable("nodes", "f8", ("node", "dim"), zlib=True)[:] = geo.nodes
            nc.createVariable("triangles", "i4", ("cell", "vertex"), zlib=True)[:] = geo.connectivity
            nc.createVariable("resistivity", "f8", ("cell",), zlib=True)[:] = model.resistivity
        else:
            put_grid(nc, geo, np.asarray(model.resistivity))


def read_netcdf(path):
    with netCDF4.Dataset(path) as nc:
        out = {k: v[:] for k, v in nc.variables.items()}
        for g in nc.groups.values():
            out.update({f"{g.name}/{k}": v[:] for k, v in g.variables.items()})
    return out


# ------------------------------------------------------------ VTK legacy
def _rect(fh, x, y, z, cell):
    fh.write(f"DATASET RECTILINEAR_GRID\nDIMENSIONS {x.size} {y.size} {z.size}\n".encode())
    for n, v in (("X", x), ("Y", y), ("Z", z)):
        fh.write(f"{n}_COORDINATES {v.size} double\n".encode())
        fh.write(np.asarray(v, ">f8").tobytes() + b"\n")
    fh.write(f"CELL_DATA {cell.size}\nSCALARS log10_rho double 1\nLOOKUP_TABLE default\n".encode())
    fh.write(np.asarray(cell, ">f8").tobytes() + b"\n")


def _nodes_from_centres(c):
    c = np.asarray(c, float)
    if c.size == 1:
        return np.array([c[0] - 0.5, c[0] + 0.5])
    m = (c[:-1] + c[1:]) / 2
    return np.concatenate([[2 * c[0] - m[0]], m, [2 * c[-1] - m[-1]]])


def write_vtk(model, path):
    geo = model.geometry
    with open(path, "wb") as fh:
        fh.write(b"# vtk DataFile Version 3.0\npcsf benchmark\nBINARY\n")
        if model.kind == "grid3d":
            xn = geo.x_nodes if geo.x_nodes is not None else _nodes_from_centres(geo.x)
            yn = geo.y_nodes if geo.y_nodes is not None else _nodes_from_centres(geo.y)
            zn = geo.z_nodes if geo.z_nodes is not None else _nodes_from_centres(geo.z)
            # VTK cell order is x fastest, then y, then z = C order of (z, y, x)
            _rect(fh, xn, yn, -zn, np.log10(model.resistivity).ravel())
        elif model.kind == "grid2d":
            xn = geo.x_nodes if geo.x_nodes is not None else _nodes_from_centres(geo.x)
            zn = geo.z_nodes if geo.z_nodes is not None else _nodes_from_centres(geo.z)
            _rect(fh, xn, np.array([0.0]), -zn, np.log10(model.resistivity).ravel())
        elif model.kind == "mesh_unstructured":
            nodes = np.asarray(geo.nodes, float)
            if nodes.shape[1] == 2:
                nodes = np.column_stack([nodes[:, 0], np.zeros(len(nodes)), -nodes[:, 1]])
            tri = np.asarray(geo.connectivity, np.int32)
            fh.write(f"DATASET UNSTRUCTURED_GRID\nPOINTS {len(nodes)} double\n".encode())
            fh.write(nodes.astype(">f8").tobytes() + b"\n")
            cells = np.column_stack([np.full(len(tri), 3, np.int32), tri]).astype(">i4")
            fh.write(f"CELLS {len(tri)} {cells.size}\n".encode())
            fh.write(cells.tobytes() + b"\n")
            fh.write(f"CELL_TYPES {len(tri)}\n".encode())
            fh.write(np.full(len(tri), 5, ">i4").tobytes() + b"\n")
            fh.write(f"CELL_DATA {len(tri)}\nSCALARS log10_rho double 1\nLOOKUP_TABLE default\n".encode())
            fh.write(np.log10(model.resistivity).astype(">f8").tobytes() + b"\n")
        else:
            raise ValueError(model.kind)


def write_vtk_any(model, base: Path):
    """multiline: one rectilinear file per line; returns list of paths."""
    if model.kind != "multiline":
        write_vtk(model, base)
        return [base]
    from pcsf import PCSFModel
    paths = []
    for line in model.geometry.lines:
        p = base.with_name(f"{base.stem}_{line.line_id}.vtk")
        write_vtk(PCSFModel(geometry=line.geometry, resistivity=line.resistivity), p)
        paths.append(p)
    return paths


def read_vtk(paths):
    """Minimal reader for the files written above (cell data only)."""
    out = []
    for p in paths:
        raw = p.read_bytes()
        i = raw.index(b"LOOKUP_TABLE default\n") + len(b"LOOKUP_TABLE default\n")
        n = int(raw[raw.index(b"CELL_DATA ") + 10:].split(b"\n", 1)[0])
        out.append(np.frombuffer(raw[i:i + 8 * n], ">f8"))
    return out


# ------------------------------------------------------------ timing
def timed(fn, *a):
    ts = []
    for _ in range(N_REPEAT):
        t0 = time.perf_counter()
        fn(*a)
        ts.append(time.perf_counter() - t0)
    return statistics.median(ts)


def main():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for label, (stem, native_files) in MODELS.items():
            model = read_pcsf(fs.DATA / f"{stem}.pcsf")
            res = {"model": label.replace("\n", " "), "native_bytes": native_size(native_files)}
            p = tmp / f"{stem}.pcsf"
            res["pcsf_write_s"] = timed(write_pcsf, model, p)
            res["pcsf_read_s"] = timed(read_pcsf, p)
            res["pcsf_bytes"] = p.stat().st_size
            p = tmp / f"{stem}.pcsm"
            res["pcsm_write_s"] = timed(write_pcsm, model, p)
            res["pcsm_read_s"] = timed(read_pcsm, p)
            res["pcsm_bytes"] = p.stat().st_size
            p = tmp / f"{stem}.pcsm.gz"
            res["pcsmgz_write_s"] = timed(write_pcsm, model, p)
            res["pcsmgz_read_s"] = timed(read_pcsm, p)
            res["pcsmgz_bytes"] = p.stat().st_size
            p = tmp / f"{stem}.nc"
            res["netcdf_write_s"] = timed(write_netcdf, model, p)
            res["netcdf_read_s"] = timed(read_netcdf, p)
            res["netcdf_bytes"] = p.stat().st_size
            base = tmp / f"{stem}.vtk"
            res["vtk_write_s"] = timed(write_vtk_any, model, base)
            vpaths = write_vtk_any(model, base)
            res["vtk_read_s"] = timed(read_vtk, vpaths)
            res["vtk_bytes"] = sum(q.stat().st_size for q in vpaths)
            rows.append(res)
            print({k: (f"{v:.4g}" if isinstance(v, float) else v) for k, v in res.items()})
    with (fs.RESULTS / "test4_storage.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    figure(rows)


def figure(rows):
    fs.apply()
    fmts = [("native", "Native", fs.GREY), ("pcsf", "PCSF", fs.C_BLUE),
            ("pcsm", "PCSM", fs.C_ORANGE), ("pcsmgz", "PCSM.gz", fs.C_RED),
            ("netcdf", "netCDF-4", fs.C_GREEN), ("vtk", "VTK", fs.C_PURPLE)]
    labels = []
    for r in rows:
        name, kind = r["model"].split(" (")
        labels.append(kind.rstrip(")"))
    x = np.arange(len(rows))
    w = 0.13
    fig, axes = plt.subplots(1, 3, figsize=(fs.DOUBLE, 0.33 * fs.DOUBLE),
                             gridspec_kw={"wspace": 0.38})
    panels = [("bytes", "File size (MB)", 1e-6, fmts),
              ("write_s", "Write time (s)", 1.0, fmts[1:]),
              ("read_s", "Read time (s)", 1.0, fmts[1:])]
    for ax, (suffix, ylab, scale, fl), letter in zip(axes, panels, "abc"):
        off = (np.arange(len(fl)) - (len(fl) - 1) / 2) * w
        for o, (k, name, c) in zip(off, fl):
            vals = np.array([r[f"{k}_{suffix}"] for r in rows], float) * scale
            ax.bar(x + o, vals, width=w, color=c, label=name, linewidth=0)
        ax.set_yscale("log")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=5.4)
        ax.set_ylabel(ylab)
        ax.tick_params(axis="x", length=0)
        fs.panel_label(ax, letter)
    axes[0].legend(ncol=6, loc="lower left", bbox_to_anchor=(0.0, 1.06),
                   fontsize=6, handlelength=1.0, columnspacing=1.2)
    fs.save(fig, "test4_storage")


def plot_only():
    with (fs.RESULTS / "test4_storage.csv").open() as fh:
        rows = [{k: (v if k == "model" else float(v)) for k, v in r.items()}
                for r in csv.DictReader(fh)]
    figure(rows)


if __name__ == "__main__":
    import sys

    plot_only() if "plot" in sys.argv else main()
