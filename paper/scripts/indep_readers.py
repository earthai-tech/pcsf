"""Readers for PCSF and PCSM written from the specification alone.

This module deliberately imports nothing from pcsf or pyCSAMT. It is
used by
test3_independent_readers.py to check that the specification is
sufficient to interpret every file used in the manuscript.

* read_pcsf_h5py(path)  -- HDF5 encoding through h5py only;
* read_pcsf_h5dump(path, dataset) -- one dataset through the HDF5
  command-line tool h5dump (the HDF5 C library), exported as raw
  little-endian binary;
* read_pcsm_text(path)  -- text encoding through a small parser of the
  PCSM grammar (Appendix B of the manuscript).

Each returns plain dictionaries of numpy arrays.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import h5py
import numpy as np

KINDS = ("grid2d", "grid3d", "mesh_unstructured", "multiline")
ENCODINGS = {"log10": lambda r: 10.0 ** r, "ln": np.exp, "linear": lambda r: r,
             "log10_conductivity": lambda r: 10.0 ** (-r), "conductivity": lambda r: 1.0 / r}


# ---------------------------------------------------------------- HDF5
def _decode(v):
    return v.decode() if isinstance(v, bytes) else v


def read_pcsf_h5py(path) -> dict:
    """Read a PCSF file with h5py and check the conformance rules."""
    out = {"arrays": {}, "checks": {}}
    with h5py.File(path, "r") as f:
        attrs = {k: _decode(v) for k, v in f.attrs.items()}
        out["attrs"] = attrs
        major = int(str(attrs["pcsf_version"]).split(".")[0])
        out["checks"]["version_major_0"] = major == 0
        out["checks"]["unit_ohm_m"] = attrs.get("resistivity_unit") == "ohm.m"
        kind = _decode(f["geometry"].attrs["kind"])
        out["kind"] = kind
        out["checks"]["kind_known"] = kind in KINDS

        def grab(name, ds):
            if isinstance(ds, h5py.Dataset) and ds.dtype.kind in "fiu":
                out["arrays"][name] = ds[()]
        f.visititems(grab)

        if kind == "multiline":
            out["checks"]["no_root_resistivity"] = "model/resistivity" not in f
            for lid in f["geometry/lines"]:
                g = f[f"geometry/lines/{lid}"]
                rho = g["resistivity"][()]
                nz = g["geometry/z"].shape[0]
                nx = g["geometry/x"].shape[0]
                out["checks"][f"shape_{lid}"] = rho.shape == (nz, nx)
            if "geometry/derived_volume" in f:
                out["checks"]["derived_volume_synthesized"] = bool(
                    f["geometry/derived_volume"].attrs.get("synthesized", False))
        else:
            rho = f["model/resistivity"][()]
            out["checks"]["positive"] = bool(np.all(rho[np.isfinite(rho)] > 0))
            if kind == "grid2d":
                exp = (f["geometry/z"].shape[0], f["geometry/x"].shape[0])
                out["checks"]["shape"] = rho.shape == exp
            elif kind == "grid3d":
                exp = (f["geometry/z"].shape[0], f["geometry/y"].shape[0],
                       f["geometry/x"].shape[0])
                out["checks"]["shape"] = rho.shape == exp
            else:
                ntri = f["geometry/connectivity"].shape[0]
                nreg = int(f["geometry/region_ids"][()].max()) + 1
                out["checks"]["shape"] = rho.shape[0] in (ntri, nreg)
            if "model/resistivity_native" in f:
                ds = f["model/resistivity_native"]
                enc = _decode(ds.attrs.get("encoding", f["model"].attrs.get("encoding")))
                lin = ENCODINGS[enc](ds[()])
                if lin.shape != rho.shape and "model/resistivity_by_node" in f:
                    # native values of a per-node prediction map to the
                    # node table, from which the cell values are derived
                    rho = f["model/resistivity_by_node"][()]
                ok = np.isfinite(lin) & np.isfinite(rho)
                rel = np.abs(lin[ok] - rho[ok]) / np.abs(rho[ok])
                out["checks"]["native_consistent"] = bool(rel.max() < 1e-12)
                out["max_rel_native"] = float(rel.max())
    return out


def read_pcsf_h5dump(path, dataset: str) -> np.ndarray:
    """Export one float64 dataset with h5dump and read the raw bytes."""
    if shutil.which("h5dump") is None:
        raise SystemExit(
            "h5dump (the HDF5 command-line tools) is not on PATH; install "
            "it, e.g. 'conda install -c conda-forge hdf5' in a separate "
            "environment or 'apt install hdf5-tools', and add it to PATH")
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "out.bin"
        subprocess.run(["h5dump", "-d", dataset, "-b", "LE", "-o", str(raw), str(path)],
                       check=True, capture_output=True)
        return np.fromfile(raw, dtype="<f8")


# ---------------------------------------------------------------- PCSM
FREE_TEXT = {"DESCRIPTION", "CREATED_BY", "CREATED_AT", "CRS", "SURVEY_JSON",
             "METADATA_JSON"}


def _num(tok):
    try:
        return float(tok)
    except ValueError:
        return tok


def read_pcsm_text(path) -> dict:
    """Parse a PCSM file into nested scopes of scalars and blocks."""
    text = Path(path).read_text(encoding="utf-8")
    if path.suffix == ".gz":
        raise ValueError("decompress first")
    root = {"scalars": {}, "blocks": {}, "scopes": {}}
    stack = [root]
    block, values = None, None
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        head = s.split(None, 1)
        if head[0] in FREE_TEXT and block is None:
            stack[-1]["scalars"][head[0]] = head[1] if len(head) > 1 else ""
            continue
        s = s.split("#", 1)[0].strip()
        if not s:
            continue
        toks = s.split()
        k = toks[0]
        if block is not None:
            if k == "END_" + block:
                stack[-1]["blocks"][block] = values
                block, values = None, None
            else:
                values.extend(_num(t) for t in toks)
            continue
        if k.endswith("_BEGIN"):
            scope = {"scalars": {}, "blocks": {}, "scopes": {}}
            name = k[:-6] + (":" + toks[1] if len(toks) > 1 else "")
            stack[-1]["scopes"][name] = scope
            stack.append(scope)
        elif k.endswith("_END"):
            stack.pop()
        elif len(toks) == 1 and k.isupper():
            block, values = k, []
        else:
            stack[-1]["scalars"][k] = [_num(t) for t in toks[1:]]
    return root


def pcsm_resistivity(doc: dict) -> dict[str, np.ndarray]:
    """Canonical resistivity arrays (keyed by line for multiline)."""
    kind = doc["scalars"]["GEOMETRY_KIND"][0]

    def shaped(scope, key="RESISTIVITY"):
        sc = scope["scalars"]
        v = np.asarray(scope["blocks"][key], dtype=float)
        if "NY" in sc:
            return v.reshape(int(sc["NZ"][0]), int(sc["NY"][0]), int(sc["NX"][0]))
        if "NX" in sc and "N_NODES" not in sc:
            return v.reshape(int(sc["NZ"][0]), int(sc["NX"][0]))
        return v

    if kind == "multiline":
        return {name.split(":", 1)[1]: shaped(scope)
                for name, scope in doc["scopes"].items() if name.startswith("LINE:")}
    return {"model": shaped(doc)}
