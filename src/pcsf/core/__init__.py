"""Core of the format: data model, encodings, versioning, I/O, records.

- :mod:`pcsf.core.schema`      -- geometry and model data classes
- :mod:`pcsf.core.encodings`   -- source-value encodings and their conversion
- :mod:`pcsf.core.versioning`  -- specification-version checks
- :mod:`pcsf.core.hdf5`        -- the PCSF (HDF5) encoding
- :mod:`pcsf.core.text`        -- the PCSM (text) encoding, optionally gzip-compressed
- :mod:`pcsf.core.record`      -- inversion record (critical inversion metadata)
- :mod:`pcsf.core.provenance`  -- provenance record of learned predictors
- :mod:`pcsf.core.conformance` -- conformance rules
"""

from .conformance import ConformanceReport, RuleResult, check_conformance
from .encodings import from_resistivity, known_encodings, to_resistivity
from .hdf5 import read_pcsf, write_pcsf
from .provenance import ModelProvenance, compute_checkpoint_hash
from .record import (
    InversionRecord,
    attach_inversion_record,
    check_inversion_record,
    get_inversion_record,
)
from .schema import (
    GEOMETRY_KINDS,
    PCSF_VERSION,
    RESISTIVITY_ENCODINGS,
    RESISTIVITY_UNIT,
    DerivedVolume,
    Grid2DGeometry,
    Grid3DGeometry,
    LineEntry,
    MultilineGeometry,
    PCSFModel,
    StationTable,
    TopographyPerStation,
    TopographyRaster,
    UnstructuredMeshGeometry,
)
from .text import pcsf_to_pcsm, pcsm_to_pcsf, read_pcsm, write_pcsm
from .versioning import check_pcsf_version, parse_pcsf_version

__all__ = [
    "GEOMETRY_KINDS", "PCSF_VERSION", "RESISTIVITY_ENCODINGS", "RESISTIVITY_UNIT",
    "ConformanceReport", "DerivedVolume", "Grid2DGeometry", "Grid3DGeometry",
    "InversionRecord", "LineEntry", "ModelProvenance", "MultilineGeometry", "PCSFModel",
    "RuleResult", "StationTable", "TopographyPerStation", "TopographyRaster",
    "UnstructuredMeshGeometry", "attach_inversion_record", "check_conformance",
    "check_inversion_record", "check_pcsf_version", "compute_checkpoint_hash",
    "from_resistivity", "get_inversion_record", "known_encodings", "parse_pcsf_version",
    "pcsf_to_pcsm", "pcsm_to_pcsf", "read_pcsf", "read_pcsm", "to_resistivity",
    "write_pcsf", "write_pcsm",
]
