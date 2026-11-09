"""pcsf -- Portable Common Subsurface Format.

An exchange format for electromagnetic inversion models, with a binary
encoding (PCSF, HDF5) and a lossless text encoding (PCSM, optionally
gzip-compressed), and the algorithms to sample and compare models of
different geometry.

Quick start::

    import pcsf

    model = pcsf.read("model.pcsf")
    print(pcsf.info(model))
    report = pcsf.validate(model)
    pcsf.write(model, "model.pcsm.gz")
"""

from ._version import FORMAT_VERSION, __version__
from .api import convert, detect, info, read, validate, write
from .core import (
    DerivedVolume,
    Grid2DGeometry,
    Grid3DGeometry,
    InversionRecord,
    LineEntry,
    ModelProvenance,
    MultilineGeometry,
    PCSFModel,
    StationTable,
    TopographyPerStation,
    TopographyRaster,
    UnstructuredMeshGeometry,
    attach_inversion_record,
    check_conformance,
    check_inversion_record,
    get_inversion_record,
    pcsf_to_pcsm,
    pcsm_to_pcsf,
    read_pcsf,
    read_pcsm,
    write_pcsf,
    write_pcsm,
)
from .exceptions import (
    ConformanceError,
    EncodingError,
    FormatError,
    GeometryError,
    MissingDependencyError,
    PCSFError,
    PCSMSyntaxError,
    VersionError,
)

__all__ = [
    "FORMAT_VERSION", "__version__",
    # facade
    "convert", "detect", "info", "read", "validate", "write",
    # data model
    "DerivedVolume", "Grid2DGeometry", "Grid3DGeometry", "InversionRecord", "LineEntry",
    "ModelProvenance", "MultilineGeometry", "PCSFModel", "StationTable",
    "TopographyPerStation", "TopographyRaster", "UnstructuredMeshGeometry",
    # encodings and records
    "attach_inversion_record", "check_conformance", "check_inversion_record",
    "get_inversion_record", "pcsf_to_pcsm", "pcsm_to_pcsf", "read_pcsf", "read_pcsm",
    "write_pcsf", "write_pcsm",
    # errors
    "ConformanceError", "EncodingError", "FormatError", "GeometryError",
    "MissingDependencyError", "PCSFError", "PCSMSyntaxError", "VersionError",
]
