"""Opening of PCSF files and native solver runs for PCSF Studio.

:func:`open_source` turns whatever the user drops on the window, a
``.pcsf``/``.pcsm`` file, a native result file or a run folder, into
a :class:`~pcsf.PCSFModel` through :func:`pcsf.read` or the adapters
of :mod:`pcsf.adapters`. It needs no Qt, so it is tested and usable
on its own.

======================== ========================================
Input                    Read with
======================== ========================================
``.pcsf``, ``.pcsm``,    :func:`pcsf.read`
``.pcsm.gz``
``.nc``                  :func:`~pcsf.adapters.emc_to_pcsf`
``.rho`` (ModEM)         :func:`~pcsf.adapters.modem_to_pcsf`
``.resistivity``         :func:`~pcsf.adapters.mare2dem_to_pcsf`
(MARE2DEM)
folder                   the solver whose files it contains
======================== ========================================
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path

from ..core.hdf5 import read_pcsf
from ..core.schema import PCSFModel
from ..core.text import read_pcsm
from ..exceptions import FormatError

__all__ = ["SOURCE_KINDS", "LoadedModel", "open_source"]

#: Kinds of input :func:`open_source` recognises.
SOURCE_KINDS = ("pcsf", "pcsm", "emc", "modem", "mare2dem", "occam2d")

_CREATED_BY = "PCSF Studio"


@dataclass
class LoadedModel:
    """A model opened by PCSF Studio and where it came from.

    Parameters
    ----------
    model : PCSFModel
        The model.
    path : Path
        File or folder that was opened.
    kind : str
        One of :data:`SOURCE_KINDS`.
    files : list of Path, optional
        Native files the adapter read, for display.
    warnings : list of str, optional
        Messages of the warnings raised while reading, for
        example an unresolved station Z convention.
    """

    model: PCSFModel
    path: Path
    kind: str
    files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        """Short label: file name and kind, for window titles."""
        return f"{self.path.name} ({self.kind})"


def _iteration(path: Path) -> int:
    """Iteration number in a solver file name (-1 when absent)."""
    found = re.findall(r"(\d+)", path.stem)
    return int(found[-1]) if found else -1


def _latest(paths: list[Path]) -> Path:
    return max(paths, key=lambda p: (_iteration(p), p.name))


def _single(folder: Path, pattern: str) -> Path | None:
    """The only file matching *pattern* in *folder*, else None."""
    found = sorted(folder.glob(pattern))
    return found[0] if len(found) == 1 else None


def _modem(rho: Path) -> tuple[PCSFModel, list[Path]]:
    from ..adapters.modem import modem_to_pcsf

    data = _single(rho.parent, "*.dat")
    log = _single(rho.parent, "*.log")
    model = modem_to_pcsf(
        rho, data=data, log=log, created_by=_CREATED_BY
    )
    return model, [p for p in (rho, data, log) if p is not None]


def _mare2dem(res: Path) -> tuple[PCSFModel, list[Path]]:
    from ..adapters.mare2dem import mare2dem_to_pcsf

    log = _single(res.parent, "*.logfile")
    model = mare2dem_to_pcsf(res, log=log, created_by=_CREATED_BY)
    return model, [p for p in (res, log) if p is not None]


def _folder(folder: Path) -> tuple[PCSFModel, str, list[Path]]:
    """Read a run folder with the solver whose files it holds."""
    rho = sorted(folder.glob("*.rho"))
    res = [
        p
        for p in folder.glob("*.resistivity")
        if re.search(r"\.\d+\.resistivity$", p.name)
    ]
    if (folder / "Occam2DMesh").exists() or list(
        folder.glob("*.iter")
    ):
        from ..adapters.occam2d import occam2d_to_pcsf

        model = occam2d_to_pcsf(folder, created_by=_CREATED_BY)
        return model, "occam2d", sorted(folder.iterdir())
    if rho:
        model, files = _modem(_latest(rho))
        return model, "modem", files
    if res:
        model, files = _mare2dem(_latest(res))
        return model, "mare2dem", files
    raise FormatError(
        f"{folder}: no Occam2D, ModEM or MARE2DEM run found "
        "(looked for Occam2DMesh or *.iter, *.rho, *.N.resistivity)"
    )


def open_source(path: str | PathLike[str]) -> LoadedModel:
    """Open a PCSF file, a native result file or a run folder.

    Parameters
    ----------
    path : path-like
        ``.pcsf``, ``.pcsm`` or ``.pcsm.gz`` file; EMC netCDF
        (``.nc``); ModEM model (``.rho``); MARE2DEM model
        (``.N.resistivity``); or a folder holding an Occam2D,
        ModEM or MARE2DEM run. For a folder, the last iteration
        is read. A ModEM or MARE2DEM file is read together with
        the data file and log next to it when there is exactly
        one of each.

    Returns
    -------
    LoadedModel
        The model, the kind of source and the warnings raised.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    FormatError
        If the file type or the folder content is not recognised,
        or the file is malformed.
    MissingDependencyError
        If the source needs an optional dependency that is not
        installed (``netCDF4`` for EMC, ``triangle`` for MARE2DEM).

    Examples
    --------
    >>> from pcsf import datasets
    >>> from pcsf.studio.sources import open_source
    >>> loaded = open_source(datasets.path("occam2d_tiny"))
    >>> loaded.kind, loaded.model.kind
    ('occam2d', 'grid2d')
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        files: list[Path] = [path]
        name = path.name.lower()
        if path.is_dir():
            model, kind, files = _folder(path)
        elif name.endswith(".pcsf"):
            model, kind = read_pcsf(path), "pcsf"
        elif name.endswith((".pcsm", ".pcsm.gz")):
            model, kind = read_pcsm(path), "pcsm"
        elif name.endswith(".nc"):
            from ..adapters.emc import emc_to_pcsf

            model = emc_to_pcsf(path, created_by=_CREATED_BY)
            kind = "emc"
        elif name.endswith(".rho"):
            model, files = _modem(path)
            kind = "modem"
        elif name.endswith(".resistivity"):
            model, files = _mare2dem(path)
            kind = "mare2dem"
        else:
            raise FormatError(
                f"{path.name}: not a PCSF, PCSM, EMC, ModEM or "
                "MARE2DEM file"
            )
    messages = list(dict.fromkeys(str(w.message) for w in caught))
    return LoadedModel(model, path, kind, files, messages)
