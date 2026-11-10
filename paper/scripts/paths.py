"""Locations of the paper's data and outputs.

Every script takes its paths from here. Defaults:

- data, from the Zenodo archive (``fetch_data.py``): ``paper/data``;
- outputs (results tables, figures, rebuilt models):
  ``paper/output``.

Environment variables override them:

``PCSF_PAPER_DATA``
    Folder holding the unpacked archive.
``PCSF_PAPER_OUT``
    Folder receiving ``results/``, ``figures/`` and ``models/``.
``PCSF_PAPER_MODELS``
    Folder of the ``.pcsf``/``.pcsm`` models the analyses read;
    ``run_all.py --rebuild`` points it to the rebuilt models.
"""

from __future__ import annotations

import os
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("PCSF_PAPER_DATA", PAPER / "data"))
OUT = Path(os.environ.get("PCSF_PAPER_OUT", PAPER / "output"))
MODELS = Path(os.environ.get("PCSF_PAPER_MODELS", DATA / "models"))
RESULTS = OUT / "results"
FIGURES = OUT / "figures"

NATIVE = DATA / "native"
#: Occam2D run of the Tongkeng CSAMT line.
TONGKENG = NATIVE / "occam2d" / "tongkeng"
#: Occam2D runs of the Baohuashan lines (``L18PLT`` ... ``L34PLT``).
OCCAM_BAOHUASHAN = NATIVE / "occam2d" / "baohuashan"
#: ModEM 3D inversion of the Baohuashan survey.
MODEM_FIELD = NATIVE / "modem" / "baohuashan"
#: ModEM 3D sample run (WILLY line 02, 27 frequencies).
MODEM_SAMPLE = NATIVE / "modem" / "sample"
#: MARE2DEM demonstration inversion.
MARE2DEM = NATIVE / "mare2dem" / "demo"
#: EMC netCDF files and the solver models they were derived from.
EMC = NATIVE / "emc"
#: Processed EDI files of the Baohuashan lines (rebuild only).
EDI = DATA / "edi" / "baohuashan"
#: Tables shipped with the data (Occam2D run summary).
TABLES = DATA / "tables"
#: Other inputs of the rebuild (station tables, synthetic models).
REBUILD = DATA / "rebuild"


def require(path: Path) -> Path:
    """Return *path*, or stop with a hint when the data is missing."""
    if not path.exists():
        raise SystemExit(
            f"{path} not found. Download the data first:\n"
            "    python paper/fetch_data.py"
        )
    return path
