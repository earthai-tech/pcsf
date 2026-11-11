"""Conversion of solver runs to PCSF and PCSM, for PCSF Studio.

:func:`convert_source` reads one source, a run folder or a result
file of Occam2D, ModEM or MARE2DEM, an EMC netCDF file or a PCSF or
PCSM file, with :func:`~pcsf.studio.sources.open_source`, and
writes it in one or more encodings. The Convert page of PCSF Studio
calls it once per row of its list; it needs no Qt, so it can be
tested and scripted on its own.

=========== ============ =====================================
Format      Suffix       Encoding
=========== ============ =====================================
``pcsf``    ``.pcsf``    HDF5, binary and compressed
``pcsm``    ``.pcsm``    plain text, readable and diff-friendly
``pcsm.gz`` ``.pcsm.gz`` gzip-compressed text
=========== ============ =====================================

All three hold the same model and convert into each other without
loss (:func:`pcsf.convert`).
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path

from ..api import validate, write
from .sources import open_source

__all__ = [
    "FORMATS",
    "ConversionResult",
    "convert_source",
    "default_stem",
    "output_paths",
]

#: Output formats, mapped to their file suffix.
FORMATS: dict[str, str] = {
    "pcsf": ".pcsf",
    "pcsm": ".pcsm",
    "pcsm.gz": ".pcsm.gz",
}

#: Suffixes removed from a file name to name the converted model,
#: longest first so that ``.pcsm.gz`` goes before ``.gz``.
_STRIP = (".pcsm.gz", ".pcsf", ".pcsm", ".nc", ".rho", ".resistivity")


@dataclass
class ConversionResult:
    """What :func:`convert_source` read and wrote.

    Parameters
    ----------
    source : Path
        File or folder that was read.
    kind : str
        Kind of the source, one of
        :data:`~pcsf.studio.sources.SOURCE_KINDS`.
    model_kind : str
        Geometry kind of the model (``grid2d``, ``grid3d``,
        ``mesh_unstructured`` or ``multiline``).
    outputs : list of Path
        Files written, in the order of the requested formats.
    warnings : list of str, optional
        Messages of the warnings raised while reading.
    conformance : bool or None, optional
        True when every conformance rule passed, False when one
        failed, None when the model was not validated.
    failures : list of str, optional
        ``"rule: message"`` of each failed rule.
    seconds : float, optional
        Wall-clock time of the conversion, in seconds.
    """

    source: Path
    kind: str
    model_kind: str
    outputs: list[Path]
    warnings: list[str] = field(default_factory=list)
    conformance: bool | None = None
    failures: list[str] = field(default_factory=list)
    seconds: float = 0.0


def default_stem(path: str | PathLike[str]) -> str:
    """Name of the converted model, from its source.

    A folder gives its own name; a file gives its name without the
    known suffix, so that ``m_NLCG_100.rho`` gives ``m_NLCG_100``
    and ``demo.6.resistivity`` gives ``demo.6``.

    Parameters
    ----------
    path : path-like
        Source file or folder. It need not exist.

    Returns
    -------
    str
        The stem, never empty (``"model"`` as a last resort).

    Examples
    --------
    >>> from pcsf.studio.convert import default_stem
    >>> default_stem("runs/demo.6.resistivity")
    'demo.6'
    >>> default_stem("model.pcsm.gz")
    'model'
    """
    path = Path(path)
    name = path.name
    if not path.is_dir():
        low = name.lower()
        for suffix in _STRIP:
            if low.endswith(suffix):
                name = name[: -len(suffix)]
                break
    return name or "model"


def _formats(formats: Iterable[str]) -> list[str]:
    chosen = list(dict.fromkeys(str(f).lower() for f in formats))
    if not chosen:
        raise ValueError("choose at least one output format")
    unknown = [f for f in chosen if f not in FORMATS]
    if unknown:
        raise ValueError(
            f"unknown format(s) {unknown}; use {sorted(FORMATS)}"
        )
    return chosen


def output_paths(
    source: str | PathLike[str],
    formats: Iterable[str] = ("pcsf",),
    out_dir: str | PathLike[str] | None = None,
    stem: str | None = None,
) -> list[Path]:
    """Files that :func:`convert_source` would write.

    Parameters
    ----------
    source : path-like
        Source file or folder.
    formats : iterable of str, default ("pcsf",)
        Keys of :data:`FORMATS`; duplicates are ignored.
    out_dir : path-like, optional
        Folder of the outputs; the folder that holds *source* by
        default (for a run folder, its parent).
    stem : str, optional
        Name of the outputs without suffix;
        :func:`default_stem` of *source* by default.

    Returns
    -------
    list of Path
        One path per format, in the order given.

    Raises
    ------
    ValueError
        If *formats* is empty or holds an unknown format.

    Examples
    --------
    >>> from pcsf.studio.convert import output_paths
    >>> [p.name for p in output_paths(
    ...     "run/m_NLCG_100.rho", ["pcsf", "pcsm.gz"], out_dir="out"
    ... )]
    ['m_NLCG_100.pcsf', 'm_NLCG_100.pcsm.gz']
    """
    source = Path(source)
    folder = Path(out_dir) if out_dir else source.parent
    name = stem or default_stem(source)
    return [folder / f"{name}{FORMATS[f]}" for f in _formats(formats)]


def convert_source(
    source: str | PathLike[str],
    formats: Iterable[str] = ("pcsf",),
    out_dir: str | PathLike[str] | None = None,
    stem: str | None = None,
    check: bool = True,
    overwrite: bool = False,
) -> ConversionResult:
    """Read a solver run or model file and write it as PCSF/PCSM.

    Parameters
    ----------
    source : path-like
        Run folder or result file of Occam2D, ModEM or MARE2DEM,
        EMC netCDF file, or PCSF/PCSM file; see
        :func:`~pcsf.studio.sources.open_source`.
    formats : iterable of str, default ("pcsf",)
        Output formats, keys of :data:`FORMATS`.
    out_dir : path-like, optional
        Folder of the outputs, created if needed; next to the
        source by default.
    stem : str, optional
        Name of the outputs without suffix; from the source by
        default (:func:`default_stem`).
    check : bool, default True
        Check the model against the conformance rules
        (:func:`pcsf.validate`) after reading it. A failed rule is
        reported in the result; the files are still written.
    overwrite : bool, default False
        Replace existing output files.

    Returns
    -------
    ConversionResult
        Source kind, geometry kind, files written, reading
        warnings and conformance.

    Raises
    ------
    ValueError
        If *formats* is empty or unknown, or an output would
        replace the source itself.
    FileExistsError
        If an output exists and *overwrite* is False. Nothing is
        read or written in that case.
    FileNotFoundError, FormatError, MissingDependencyError
        As :func:`~pcsf.studio.sources.open_source`, when the
        source cannot be read.

    See Also
    --------
    pcsf.studio.sources.open_source : Reading of the sources.
    pcsf.convert : Conversion between PCSF and PCSM files.

    Examples
    --------
    >>> import tempfile
    >>> from pcsf import datasets
    >>> from pcsf.studio.convert import convert_source
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     res = convert_source(
    ...         datasets.path("occam2d_tiny"),
    ...         ["pcsf", "pcsm.gz"],
    ...         out_dir=tmp,
    ...     )
    ...     [p.name for p in res.outputs], res.kind, res.conformance
    (['occam2d_tiny.pcsf', 'occam2d_tiny.pcsm.gz'], 'occam2d', True)
    """
    started = time.perf_counter()
    source = Path(source)
    targets = output_paths(source, formats, out_dir, stem)
    for target in targets:
        if source.exists() and target.resolve() == source.resolve():
            raise ValueError(
                f"{target.name}: the output would replace the source"
            )
        if target.exists() and not overwrite:
            raise FileExistsError(
                f"{target} exists (allow overwriting to replace it)"
            )
    loaded = open_source(source)
    conformance: bool | None = None
    failures: list[str] = []
    if check:
        report = validate(loaded.model)
        conformance = report.passed
        failures = [f"{r.rule}: {r.message}" for r in report.failures]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        write(loaded.model, target)
    return ConversionResult(
        source=source,
        kind=loaded.kind,
        model_kind=loaded.model.kind,
        outputs=targets,
        warnings=list(loaded.warnings),
        conformance=conformance,
        failures=failures,
        seconds=time.perf_counter() - started,
    )
