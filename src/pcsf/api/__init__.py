"""Stable public interface of pcsf.

Everything importable from :mod:`pcsf.api` (and re-exported by
:mod:`pcsf`) follows semantic versioning: it changes only in a major
release, after a deprecation period. Modules outside ``pcsf.api`` are
internal and may change between minor releases.

Typical use::

    import pcsf

    model = pcsf.read("model.pcsf")          # or .pcsm / .pcsm.gz
    print(pcsf.info(model))
    pcsf.validate(model).raise_if_failed()
    pcsf.write(model, "model.pcsm")
    pcsf.convert("model.pcsm.gz", "model.pcsf")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Union

import numpy as np

from ..core.conformance import ConformanceReport, check_conformance
from ..core.hdf5 import read_pcsf, write_pcsf
from ..core.record import check_inversion_record, get_inversion_record
from ..core.schema import PCSFModel
from ..core.text import read_pcsm, write_pcsm
from ..exceptions import FormatError
from ..utils.io import suffixes

__all__ = ["convert", "detect", "info", "read", "validate", "write"]

PathOrModel = Union[str, "os.PathLike[str]", PCSFModel]

_HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
_GZIP_MAGIC = b"\x1f\x8b"


def detect(path: str | os.PathLike[str]) -> str:
    """Encoding of a file from its content: ``"pcsf"``, ``"pcsm"`` or ``"pcsm.gz"``.

    The extension is not trusted; the first bytes decide.
    """
    with open(path, "rb") as fh:
        head = fh.read(512)
    if head.startswith(_HDF5_MAGIC):
        return "pcsf"
    if head.startswith(_GZIP_MAGIC):
        return "pcsm.gz"
    text = head.decode("utf-8", errors="replace")
    if "PCSM_VERSION" in text:
        return "pcsm"
    raise FormatError(f"{path}: not a PCSF (HDF5) or PCSM (text) file")


def read(path: str | os.PathLike[str]) -> PCSFModel:
    """Read a model from PCSF, PCSM or PCSM.gz, detected from the content."""
    kind = detect(path)
    return read_pcsf(path) if kind == "pcsf" else read_pcsm(path)


def write(model: PCSFModel, path: str | os.PathLike[str], **kwargs: Any) -> Path:
    """Write *model*; the encoding follows the suffix (``.pcsf``, ``.pcsm``, ``.pcsm.gz``).

    Extra keyword arguments go to the PCSM writer (e.g. ``log10_view=True``).
    """
    suf = suffixes(path)
    if suf.endswith(".pcsf") or suf.endswith(".h5") or suf.endswith(".hdf5"):
        if kwargs:
            raise TypeError(f"unexpected arguments for PCSF: {sorted(kwargs)}")
        return write_pcsf(model, path)
    if suf.endswith(".pcsm") or suf.endswith(".pcsm.gz"):
        return write_pcsm(model, path, **kwargs)
    raise FormatError(f"{path}: suffix must be .pcsf, .pcsm or .pcsm.gz")


def convert(src: str | os.PathLike[str], dst: str | os.PathLike[str], **kwargs: Any) -> Path:
    """Read *src* in any encoding and write it to *dst* (lossless)."""
    return write(read(src), dst, **kwargs)


def validate(model: PathOrModel) -> ConformanceReport:
    """Check the conformance rules on a model or a file."""
    m = model if isinstance(model, PCSFModel) else read(model)
    return check_conformance(m)


def info(model: PathOrModel) -> dict[str, Any]:
    """Short description of a model: kind, shape, encoding, stations, record."""
    m = model if isinstance(model, PCSFModel) else read(model)
    out: dict[str, Any] = {"kind": m.kind, "source_backend": m.source_backend,
                           "crs": m.crs, "description": m.description}
    if m.kind == "multiline":
        out["lines"] = [ln.line_id for ln in m.geometry.lines]
        out["n_cells"] = int(sum(np.asarray(ln.resistivity).size for ln in m.geometry.lines))
    else:
        rho = np.asarray(m.resistivity, float)
        out["shape"] = tuple(rho.shape)
        out["n_cells"] = int(rho.size)
        fin = rho[np.isfinite(rho)]
        if fin.size:
            out["resistivity_range_ohm_m"] = (float(fin.min()), float(fin.max()))
    out["native_encoding"] = m.resistivity_native_encoding
    out["n_stations"] = 0 if m.stations is None else len(m.stations.name)
    rec = get_inversion_record(m)
    if rec is not None:
        miss = check_inversion_record(rec)
        out["inversion_record"] = {"solver": rec.solver,
                                   "final_rms": rec.misfit.get("final_rms"),
                                   "termination": rec.misfit.get("termination"),
                                   "missing_required": miss["required"]}
    return out
