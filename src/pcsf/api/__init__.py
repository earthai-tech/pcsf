"""Stable public interface of pcsf.

Everything importable from :mod:`pcsf.api`, and re-exported by
:mod:`pcsf`, follows semantic versioning: it changes only in a major
release, after a deprecation period. Modules outside ``pcsf.api`` are
internal and may change between minor releases.

Examples
--------
>>> import os, tempfile
>>> import pcsf
>>> model = pcsf.PCSFModel(
...     geometry=pcsf.Grid2DGeometry(x=[0.0, 10.0], z=[5.0]),
...     resistivity=[[10.0, 1000.0]],
... )
>>> with tempfile.TemporaryDirectory() as tmp:
...     path = pcsf.write(model, os.path.join(tmp, "m.pcsm.gz"))
...     out = pcsf.convert(path, os.path.join(tmp, "m.pcsf"))
...     pcsf.detect(out), pcsf.validate(out).passed
('pcsf', True)
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

#: A model in memory or the path of a file holding one.
PathOrModel = Union[str, "os.PathLike[str]", PCSFModel]

_HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
_GZIP_MAGIC = b"\x1f\x8b"
_HDF5_SUFFIXES = (".pcsf", ".h5", ".hdf5")
_PCSM_SUFFIXES = (".pcsm", ".pcsm.gz")


def _as_model(model: PathOrModel) -> PCSFModel:
    """Return *model* itself or the model read from that path."""
    return model if isinstance(model, PCSFModel) else read(model)


def detect(path: str | os.PathLike[str]) -> str:
    """Encoding of a file, decided from its content.

    Parameters
    ----------
    path : str or os.PathLike
        File to inspect. Only the first 512 bytes are read.

    Returns
    -------
    {"pcsf", "pcsm", "pcsm.gz"}
        ``"pcsf"`` for HDF5, ``"pcsm.gz"`` for gzip-compressed text
        and ``"pcsm"`` for plain text with a ``PCSM_VERSION`` line.

    Raises
    ------
    FormatError
        If the content matches none of the encodings.
    OSError
        If the file cannot be opened.

    See Also
    --------
    read : Read a file of any encoding.

    Notes
    -----
    The file extension is never trusted: a renamed file is still
    recognised. A gzip file is reported as ``"pcsm.gz"`` without
    being decompressed; :func:`read` checks its content.

    Examples
    --------
    >>> import os, tempfile
    >>> import pcsf
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0], z=[5.0]),
    ...     resistivity=[[100.0]],
    ... )
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     path = pcsf.write(model, os.path.join(tmp, "m.pcsm"))
    ...     pcsf.detect(path)
    'pcsm'
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
    """Read a model from a PCSF, PCSM or PCSM.gz file.

    Parameters
    ----------
    path : str or os.PathLike
        File to read; the encoding is detected from the content.

    Returns
    -------
    PCSFModel
        The model, with canonical linear resistivity in ohm m and,
        when stored, the source values and their encoding.

    Raises
    ------
    FormatError
        If the encoding is not recognised or the file is malformed.
    VersionError
        If the file was written with an unsupported major format
        version.

    See Also
    --------
    detect : Encoding detection used here.
    write : Inverse operation.

    Examples
    --------
    >>> import os, tempfile
    >>> import pcsf
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0, 10.0], z=[5.0]),
    ...     resistivity=[[10.0, 1000.0]],
    ... )
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     path = pcsf.write(model, os.path.join(tmp, "m.pcsf"))
    ...     back = pcsf.read(path)
    >>> print(back.resistivity)
    [[  10. 1000.]]
    """
    kind = detect(path)
    return read_pcsf(path) if kind == "pcsf" else read_pcsm(path)


def write(
    model: PCSFModel, path: str | os.PathLike[str], **kwargs: Any
) -> Path:
    """Write a model, choosing the encoding from the file suffix.

    Parameters
    ----------
    model : PCSFModel
        Model to write.
    path : str or os.PathLike
        Destination. Suffix ``.pcsf`` (or ``.h5``, ``.hdf5``) writes
        HDF5; ``.pcsm`` writes text and ``.pcsm.gz`` compressed text.
    **kwargs
        Options of the PCSM writer, such as ``log10_view=True``;
        not accepted for HDF5.

    Returns
    -------
    pathlib.Path
        Path of the written file.

    Raises
    ------
    FormatError
        If the suffix is not recognised.
    TypeError
        If options are given for an HDF5 file.

    See Also
    --------
    read : Inverse operation.
    convert : Read and write in one call.

    Examples
    --------
    >>> import os, tempfile
    >>> import pcsf
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0], z=[5.0]),
    ...     resistivity=[[100.0]],
    ... )
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     pcsf.write(model, os.path.join(tmp, "m.pcsm.gz")).name
    'm.pcsm.gz'
    """
    suf = suffixes(path)
    if suf.endswith(_HDF5_SUFFIXES):
        if kwargs:
            raise TypeError(
                f"unexpected arguments for PCSF: {sorted(kwargs)}"
            )
        return write_pcsf(model, path)
    if suf.endswith(_PCSM_SUFFIXES):
        return write_pcsm(model, path, **kwargs)
    raise FormatError(
        f"{path}: suffix must be .pcsf, .pcsm or .pcsm.gz"
    )


def convert(
    src: str | os.PathLike[str],
    dst: str | os.PathLike[str],
    **kwargs: Any,
) -> Path:
    """Convert a file between PCSF, PCSM and PCSM.gz.

    Parameters
    ----------
    src : str or os.PathLike
        Source file, any encoding (detected from the content).
    dst : str or os.PathLike
        Destination; its suffix selects the encoding.
    **kwargs
        Options of the PCSM writer, as in :func:`write`.

    Returns
    -------
    pathlib.Path
        Path of the written file.

    Raises
    ------
    FormatError
        If either encoding is not recognised.

    See Also
    --------
    read, write

    Notes
    -----
    The conversion is lossless: every stored array, the source
    values with their encoding, and the provenance are carried over
    bit for bit.

    Examples
    --------
    >>> import os, tempfile
    >>> import pcsf
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0], z=[5.0]),
    ...     resistivity=[[100.0]],
    ... )
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     src = pcsf.write(model, os.path.join(tmp, "m.pcsf"))
    ...     dst = pcsf.convert(src, os.path.join(tmp, "m.pcsm"))
    ...     pcsf.detect(dst)
    'pcsm'
    """
    return write(read(src), dst, **kwargs)


def validate(model: PathOrModel) -> ConformanceReport:
    """Check a model or a file against the conformance rules.

    Parameters
    ----------
    model : PCSFModel or str or os.PathLike
        Model in memory, or the path of a file to read first.

    Returns
    -------
    ConformanceReport
        One result per rule; ``report.passed`` is True when all
        pass, and ``report.raise_if_failed()`` turns failures into an
        exception.

    Raises
    ------
    FormatError
        If *model* is a path that cannot be read.

    See Also
    --------
    pcsf.core.conformance.check_conformance : Rule definitions.

    Examples
    --------
    >>> import pcsf
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0], z=[5.0]),
    ...     resistivity=[[100.0]],
    ... )
    >>> pcsf.validate(model).passed
    True
    """
    return check_conformance(_as_model(model))


def info(model: PathOrModel) -> dict[str, Any]:
    """Short description of a model.

    Parameters
    ----------
    model : PCSFModel or str or os.PathLike
        Model in memory, or the path of a file to read first.

    Returns
    -------
    dict
        Always ``kind``, ``source_backend``, ``crs``,
        ``description``, ``n_cells``, ``native_encoding`` and
        ``n_stations``. Grids and meshes add ``shape`` and, when
        finite values exist, ``resistivity_range_ohm_m`` as
        ``(min, max)``; ``multiline`` models add ``lines``. When an
        inversion record is present, ``inversion_record`` holds the
        solver, final RMS, termination and missing required fields.

    See Also
    --------
    validate : Full conformance check.

    Examples
    --------
    >>> import pcsf
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0, 10.0], z=[5.0]),
    ...     resistivity=[[10.0, 1000.0]],
    ... )
    >>> d = pcsf.info(model)
    >>> d["kind"], d["shape"], d["resistivity_range_ohm_m"]
    ('grid2d', (1, 2), (10.0, 1000.0))
    """
    m = _as_model(model)
    out: dict[str, Any] = {
        "kind": m.kind,
        "source_backend": m.source_backend,
        "crs": m.crs,
        "description": m.description,
    }
    if m.kind == "multiline":
        lines = m.geometry.lines
        out["lines"] = [ln.line_id for ln in lines]
        out["n_cells"] = int(
            sum(np.asarray(ln.resistivity).size for ln in lines)
        )
    else:
        rho = np.asarray(m.resistivity, dtype=float)
        out["shape"] = tuple(rho.shape)
        out["n_cells"] = int(rho.size)
        finite = rho[np.isfinite(rho)]
        if finite.size:
            out["resistivity_range_ohm_m"] = (
                float(finite.min()),
                float(finite.max()),
            )
    out["native_encoding"] = m.resistivity_native_encoding
    out["n_stations"] = (
        0 if m.stations is None else len(m.stations.name)
    )
    rec = get_inversion_record(m)
    if rec is not None:
        missing = check_inversion_record(rec)
        out["inversion_record"] = {
            "solver": rec.solver,
            "final_rms": rec.misfit.get("final_rms"),
            "termination": rec.misfit.get("termination"),
            "missing_required": missing["required"],
        }
    return out
