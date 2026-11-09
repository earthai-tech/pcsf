"""In-memory schema for the Portable Common Subsurface Format (PCSF).

PCSF is a solver-neutral representation of isotropic resistivity
models: results of Occam2D, ModEM, MARE2DEM, learned predictors or any
other code convert to it, so that readers, viewers and comparison tools
need one implementation. The design is described in the specification
(``spec/``) and in the accompanying Geophysics paper.

This module defines the schema only — geometry and container
dataclasses, the frozen list of supported geometry kinds, and shape
validation. Reading/writing ``.pcsf`` files lives in
:mod:`pcsf.core.hdf5`; per-backend conversion lives in
:mod:`pcsf.adapters`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

import numpy as np

from .._version import FORMAT_VERSION
from ..api.property import MetadataMixin, PCSFObject
from ..exceptions import EncodingError, GeometryError
from .encodings import (
    BUILTIN_ENCODINGS,
    is_known_encoding,
    known_encodings,
)

__all__ = [
    "DERIVATION_METHODS",
    "GEOMETRY_KINDS",
    "PCSF_VERSION",
    "RESISTIVITY_ENCODINGS",
    "RESISTIVITY_UNIT",
    "TOPOGRAPHY_KINDS",
    "DerivedVolume",
    "Grid2DGeometry",
    "Grid3DGeometry",
    "LineEntry",
    "MultilineGeometry",
    "PCSFModel",
    "StationTable",
    "TopographyPerStation",
    "TopographyRaster",
    "UnstructuredMeshGeometry",
]

PCSF_VERSION = FORMAT_VERSION
RESISTIVITY_UNIT = "ohm.m"
GEOMETRY_KINDS = ("grid2d", "grid3d", "mesh_unstructured", "multiline")
#: Encodings defined by the specification (plugins may register more;
#: see :mod:`pcsf.core.encodings`).
RESISTIVITY_ENCODINGS = BUILTIN_ENCODINGS
TOPOGRAPHY_KINDS = ("per_station", "raster")
DERIVATION_METHODS = ("linear_interp", "kriging", "idw")


def _arr(value: Any, *, dtype: Any = float) -> np.ndarray:
    return np.asarray(value, dtype=dtype)


def _opt_arr(value: Any, *, dtype: Any = float) -> np.ndarray | None:
    return None if value is None else np.asarray(value, dtype=dtype)


# ---------------------------------------------------------------------
# Geometry kinds
# ---------------------------------------------------------------------


@dataclass(repr=False)
class Grid2DGeometry(PCSFObject):
    """Rectilinear geometry of one 2-D section (Occam2D).

    Parameters
    ----------
    x : ndarray (n_x,)
        Real station chainage, metres — never a solver's mesh-local
        frame (see the Occam2D coordinate-frame note in
        the Occam2D adapter).
    z : ndarray (n_z,)
        Depth cell centres, metres, positive downward.
    x_nodes, z_nodes : ndarray, optional
        Cell-edge coordinates, one longer than *x*/*z*.
    origin : ndarray (2,), optional
        Real-world offset when *x* is locally referenced.
    azimuth_deg : float, optional
        Profile bearing, for georeferencing back to the survey line.

    See Also
    --------
    Grid3DGeometry, UnstructuredMeshGeometry

    Examples
    --------
    >>> from pcsf import Grid2DGeometry
    >>> g = Grid2DGeometry(x=[0.0, 50.0, 100.0], z=[5.0, 15.0])
    >>> g.resistivity_shape
    (2, 3)
    """

    kind: ClassVar[str] = "grid2d"

    x: np.ndarray
    z: np.ndarray
    x_nodes: np.ndarray | None = None
    z_nodes: np.ndarray | None = None
    origin: np.ndarray | None = None
    azimuth_deg: float | None = None

    def __post_init__(self) -> None:
        self.x = _arr(self.x)
        self.z = _arr(self.z)
        self.x_nodes = _opt_arr(self.x_nodes)
        self.z_nodes = _opt_arr(self.z_nodes)
        self.origin = _opt_arr(self.origin)

    def validate(self) -> None:
        """Check the consistency of the arrays.

        Raises
        ------
        GeometryError
            If *x* or *z* is not 1-D, a node array does not
            have one more element than its centres, or
            *origin* does not have shape (2,).
        """
        if self.x.ndim != 1 or self.z.ndim != 1:
            raise GeometryError("Grid2DGeometry.x and .z must be 1-D")
        if self.x_nodes is not None and self.x_nodes.shape != (
            self.x.shape[0] + 1,
        ):
            raise GeometryError(
                "x_nodes must have one more element than x"
            )
        if self.z_nodes is not None and self.z_nodes.shape != (
            self.z.shape[0] + 1,
        ):
            raise GeometryError(
                "z_nodes must have one more element than z"
            )
        if self.origin is not None and self.origin.shape != (2,):
            raise GeometryError("origin must have shape (2,)")

    @property
    def resistivity_shape(self) -> tuple[int, int]:
        """Shape ``(n_z, n_x)`` of the resistivity array."""
        return (self.z.shape[0], self.x.shape[0])


@dataclass(repr=False)
class Grid3DGeometry(PCSFObject):
    """Native 3-D tensor volume geometry (ModEM).

    Parameters
    ----------
    x, y, z : ndarray
        Cell-centre coordinates, metres.
    x_nodes, y_nodes, z_nodes : ndarray, optional
        Cell-edge coordinates.
    origin : ndarray (3,), optional
        Real-world grid origin.
    rotation_deg : float, default 0.0
        Grid rotation about the vertical axis.
    n_air : int, default 0
        Explicit air-layer count (unlike Occam2D's inferred count).

    Examples
    --------
    >>> from pcsf.core.schema import Grid3DGeometry
    >>> g = Grid3DGeometry(x=[0.0, 1.0], y=[0.0], z=[1.0, 2.0, 3.0])
    >>> g.resistivity_shape
    (3, 1, 2)
    """

    kind: ClassVar[str] = "grid3d"

    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    x_nodes: np.ndarray | None = None
    y_nodes: np.ndarray | None = None
    z_nodes: np.ndarray | None = None
    origin: np.ndarray | None = None
    rotation_deg: float = 0.0
    n_air: int = 0

    def __post_init__(self) -> None:
        self.x = _arr(self.x)
        self.y = _arr(self.y)
        self.z = _arr(self.z)
        self.x_nodes = _opt_arr(self.x_nodes)
        self.y_nodes = _opt_arr(self.y_nodes)
        self.z_nodes = _opt_arr(self.z_nodes)
        self.origin = _opt_arr(self.origin)

    def validate(self) -> None:
        """Check the consistency of the arrays.

        Raises
        ------
        GeometryError
            If a centre array is not 1-D or a node array does
            not have one more element than its centres.
        """
        if self.x.ndim != 1 or self.y.ndim != 1 or self.z.ndim != 1:
            raise GeometryError("Grid3DGeometry.x, .y, .z must be 1-D")
        if self.origin is not None and self.origin.shape != (3,):
            raise GeometryError("origin must have shape (3,)")
        if self.n_air < 0:
            raise GeometryError("n_air must be >= 0")

    @property
    def resistivity_shape(self) -> tuple[int, int, int]:
        # Deliberately (n_z, n_y, n_x) — matches ModEM's own native
        # order, to avoid introducing a second axis-order transpose
        # bug.
        return (self.z.shape[0], self.y.shape[0], self.x.shape[0])


@dataclass(repr=False)
class UnstructuredMeshGeometry(PCSFObject):
    """Native unstructured triangular mesh geometry (MARE2DEM).

    Preserves the mesh as-is (no forced regrid onto a tensor grid), so
    a MARE2DEM result keeps its real element resolution.

    Parameters
    ----------
    nodes : ndarray (n, 2) or (n, 3)
        Node coordinates, metres.
    connectivity : ndarray (m, 3), int
        Triangle node indices.
    region_ids : ndarray (m,), int
        Region id per triangle.
    plane : {"xz", "xy", "3d"}, default "xz"
        Physical plane the mesh lives in. MARE2DEM profiles are
        conventionally in ``(y, z)`` but stored generically as
        ``plane="xz"`` with *x* holding the profile's own along-line
        coordinate.

    Examples
    --------
    >>> from pcsf.core.schema import UnstructuredMeshGeometry
    >>> mesh = UnstructuredMeshGeometry(
    ...     nodes=[[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
    ...     connectivity=[[0, 1, 2]],
    ...     region_ids=[0],
    ... )
    >>> mesh.n_regions
    1
    """

    kind: ClassVar[str] = "mesh_unstructured"

    nodes: np.ndarray
    connectivity: np.ndarray
    region_ids: np.ndarray
    plane: str = "xz"

    def __post_init__(self) -> None:
        self.nodes = _arr(self.nodes)
        self.connectivity = _arr(self.connectivity, dtype=np.int64)
        self.region_ids = _arr(self.region_ids, dtype=np.int32)

    def validate(self) -> None:
        """Check the consistency of the arrays.

        Raises
        ------
        GeometryError
            If an array has the wrong shape, *plane* is
            unknown, or the connectivity references a node
            that does not exist.
        """
        if self.nodes.ndim != 2 or self.nodes.shape[1] not in (2, 3):
            raise GeometryError(
                "nodes must have shape (n, 2) or (n, 3)"
            )
        if (
            self.connectivity.ndim != 2
            or self.connectivity.shape[1] != 3
        ):
            raise GeometryError("connectivity must have shape (m, 3)")
        if self.region_ids.shape != (self.connectivity.shape[0],):
            raise GeometryError(
                "region_ids must have one entry per triangle"
            )
        if self.plane not in ("xz", "xy", "3d"):
            raise GeometryError(
                "plane must be one of 'xz'/'xy'/'3d', "
                f"got {self.plane!r}"
            )
        n_nodes = self.nodes.shape[0]
        if self.connectivity.size and (
            self.connectivity.min() < 0
            or self.connectivity.max() >= n_nodes
        ):
            raise GeometryError(
                "connectivity references an out-of-range node"
            )

    @property
    def n_regions(self) -> int:
        """Number of distinct region ids."""
        return (
            int(np.unique(self.region_ids).size)
            if self.region_ids.size
            else 0
        )


@dataclass(repr=False)
class LineEntry(PCSFObject):
    """One profile within a :class:`MultilineGeometry`.

    Parameters
    ----------
    line_id : str
        Unique identifier for this line.
    geometry : Grid2DGeometry
        The line's own 2-D section geometry.
    resistivity : ndarray (n_z, n_x)
        Canonical linear ohm.m resistivity for this line.
    offset_y : float
        Cross-line position, metres.
    offset_kind : {"real", "synthetic"}, default "synthetic"
        Whether *offset_y* comes from real survey geometry or is a
        placeholder spacing for display only.
    azimuth_deg : float, optional
        Line bearing.

    Examples
    --------
    >>> from pcsf.core.schema import Grid2DGeometry, LineEntry
    >>> line = LineEntry(
    ...     "L1", Grid2DGeometry(x=[0.0, 10.0], z=[5.0]),
    ...     resistivity=[[100.0, 200.0]], offset_y=250.0,
    ...     offset_kind="real",
    ... )
    >>> line.validate()
    """

    line_id: str
    geometry: Grid2DGeometry
    resistivity: np.ndarray
    offset_y: float = 0.0
    offset_kind: str = "synthetic"
    azimuth_deg: float | None = None

    def __post_init__(self) -> None:
        self.resistivity = _arr(self.resistivity)

    def validate(self) -> None:
        """Check the consistency of the arrays.

        Raises
        ------
        GeometryError
            If the resistivity shape does not match the
            geometry or *offset_kind* is unknown.
        """
        self.geometry.validate()
        if self.resistivity.shape != self.geometry.resistivity_shape:
            raise GeometryError(
                f"line {self.line_id!r}: resistivity shape "
                f"{self.resistivity.shape} does not match geometry "
                f"{self.geometry.resistivity_shape}"
            )
        if self.offset_kind not in ("real", "synthetic"):
            raise GeometryError(
                "offset_kind must be 'real' or 'synthetic'"
            )


@dataclass(repr=False)
class DerivedVolume(PCSFObject):
    """Optional 3-D volume synthesized from stacked lines.

    The volume is always labelled as synthesized, so that a
    reader never mistakes an interpolated stack of 2-D
    sections for a 3-D inversion (rule C7).

    Parameters
    ----------
    grid : Grid3DGeometry
        Grid of the volume.
    resistivity : ndarray of shape (n_z, n_y, n_x)
        Resistivity in ohm m.
    derivation_method : str, default "linear_interp"
        One of :data:`DERIVATION_METHODS`.
    derived_from : list of str
        Identifiers of the lines used.
    synthesized : bool, default True
        Must stay True for a conforming file.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.core.schema import DerivedVolume, Grid3DGeometry
    >>> grid = Grid3DGeometry(x=[0.0, 10.0], y=[0.0, 100.0], z=[5.0])
    >>> vol = DerivedVolume(grid, np.full((1, 2, 2), 100.0),
    ...                     derived_from=["L0", "L1"])
    >>> vol.synthesized
    True
    """

    grid: Grid3DGeometry
    resistivity: np.ndarray
    derivation_method: str = "linear_interp"
    derived_from: list[str] = field(default_factory=list)
    synthesized: bool = True

    def __post_init__(self) -> None:
        self.resistivity = _arr(self.resistivity)

    def validate(self) -> None:
        """Check the consistency of the arrays.

        Raises
        ------
        GeometryError
            If the resistivity shape does not match the grid
            or *derivation_method* is unknown.
        """
        self.grid.validate()
        if self.resistivity.shape != self.grid.resistivity_shape:
            raise GeometryError(
                "derived_volume resistivity shape "
                f"{self.resistivity.shape} "
                f"does not match grid {self.grid.resistivity_shape}"
            )
        if self.derivation_method not in DERIVATION_METHODS:
            raise GeometryError(
                "derivation_method must be one of "
                f"{DERIVATION_METHODS}, got {self.derivation_method!r}"
            )


@dataclass(repr=False)
class MultilineGeometry(PCSFObject):
    """A set of 2-D profiles with their real positions.

    Each line carries its own geometry and resistivity, so
    that fence and block views are built from stored data
    rather than reconstructed at render time. The optional
    derived volume is a documented, reproducible synthesis.

    Parameters
    ----------
    lines : list of LineEntry
        Profiles, with unique identifiers.
    derived_volume : DerivedVolume, optional
        Volume interpolated from the lines.

    Examples
    --------
    >>> from pcsf.core.schema import (Grid2DGeometry, LineEntry,
    ...                               MultilineGeometry)
    >>> geo = Grid2DGeometry(x=[0.0, 10.0], z=[5.0])
    >>> lines = [LineEntry(f"L{i}", geo, [[100.0, 200.0]], 100.0 * i)
    ...          for i in range(2)]
    >>> MultilineGeometry(lines).validate()
    """

    kind: ClassVar[str] = "multiline"

    lines: list[LineEntry] = field(default_factory=list)
    derived_volume: DerivedVolume | None = None

    def validate(self) -> None:
        """Check the consistency of the arrays.

        Raises
        ------
        GeometryError
            If there is no line, line identifiers repeat, or
            a line or the derived volume is invalid.
        """
        if not self.lines:
            raise GeometryError(
                "MultilineGeometry needs at least one line"
            )
        ids = [line.line_id for line in self.lines]
        if len(set(ids)) != len(ids):
            raise GeometryError(f"duplicate line_id values: {ids}")
        for line in self.lines:
            line.validate()
        if self.derived_volume is not None:
            self.derived_volume.validate()


# ---------------------------------------------------------------------
# Container-level tables
# ---------------------------------------------------------------------


@dataclass(repr=False)
class StationTable(PCSFObject):
    """Survey station positions, shared by all geometry kinds.

    Parameters
    ----------
    name : list of str
        Station names.
    x, y, z : ndarray of shape (n,)
        Positions in the model frame, in metres: chainage
        along the profile for ``grid2d``, the grid frame for
        ``grid3d``, the mesh frame for ``mesh_unstructured``.
        They are never geographic coordinates.
    line_id : list of str, optional
        Line of each station, for ``multiline`` models.
    lon, lat : ndarray of shape (n,), optional
        WGS84 longitude and latitude in decimal degrees;
        the only carrier of real-world position. Both or
        neither must be given.

    Examples
    --------
    >>> from pcsf.core.schema import StationTable
    >>> st = StationTable(name=["S1", "S2"], x=[0.0, 50.0],
    ...                   y=[0.0, 0.0], z=[0.0, 0.0],
    ...                   lon=[-5.0, -5.0])
    >>> st.validate()
    Traceback (most recent call last):
    ...
    pcsf.exceptions.GeometryError: StationTable.lon and .lat must ...
    """

    name: list[str] = field(default_factory=list)
    x: np.ndarray = field(default_factory=lambda: np.array([]))
    y: np.ndarray = field(default_factory=lambda: np.array([]))
    z: np.ndarray = field(default_factory=lambda: np.array([]))
    line_id: list[str] | None = None
    lon: np.ndarray | None = None
    lat: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.x = _arr(self.x)
        self.y = _arr(self.y)
        self.z = _arr(self.z)
        self.lon = _opt_arr(self.lon)
        self.lat = _opt_arr(self.lat)

    def validate(self) -> None:
        """Check the consistency of the arrays.

        Raises
        ------
        GeometryError
            If an array length differs from the number of
            names, or only one of *lon* and *lat* is set.
        """
        n = len(self.name)
        for label, arr in (
            ("x", self.x),
            ("y", self.y),
            ("z", self.z),
        ):
            if arr.shape != (n,):
                raise GeometryError(
                    f"StationTable.{label} must have shape ({n},) to "
                    f"match {n} station names, got {arr.shape}"
                )
        if self.line_id is not None and len(self.line_id) != n:
            raise GeometryError(
                "StationTable.line_id must match name length"
            )
        for label, arr in (("lon", self.lon), ("lat", self.lat)):
            if arr is not None and arr.shape != (n,):
                raise GeometryError(
                    f"StationTable.{label} must have shape ({n},) to "
                    f"match {n} station names, got {arr.shape}"
                )
        if (self.lon is None) != (self.lat is None):
            raise GeometryError(
                "StationTable.lon and .lat must be set together (or "
                "both left unset), never only one"
            )


@dataclass(repr=False)
class TopographyPerStation(PCSFObject):
    """Elevation of each station.

    Parameters
    ----------
    station_id : list of str
        Station names, matching :class:`StationTable`.
    elevation : ndarray of shape (n,)
        Elevation in metres above the vertical datum.

    Examples
    --------
    >>> from pcsf.core.schema import TopographyPerStation
    >>> topo = TopographyPerStation(["S1", "S2"], [312.5, 298.0])
    >>> topo.validate()
    """

    kind: ClassVar[str] = "per_station"

    station_id: list[str] = field(default_factory=list)
    elevation: np.ndarray = field(default_factory=lambda: np.array([]))

    def __post_init__(self) -> None:
        self.elevation = _arr(self.elevation)

    def validate(self) -> None:
        """Check the consistency of the arrays.

        Raises
        ------
        GeometryError
            If *elevation* and *station_id* differ in length.
        """
        if self.elevation.shape != (len(self.station_id),):
            raise GeometryError(
                "TopographyPerStation.elevation must match "
                "station_id length"
            )


@dataclass(repr=False)
class TopographyRaster(PCSFObject):
    """Gridded elevation surface, independent of stations.

    Unlike :class:`TopographyPerStation`, this carries no station
    identifiers at all: it is a standalone terrain surface a consumer
    can sample at any coordinate, not a per-station lookup table. It
    adds no raster-library dependency: it is built from
    ``x``, ``y`` and ``elevation`` arrays obtained by the
    caller, and pcsf never parses georeferenced raster files.

    Parameters
    ----------
    x : ndarray (n_x,)
        Grid x-coordinates (or longitude), increasing.
    y : ndarray (n_y,)
        Grid y-coordinates (or latitude), increasing.
    elevation : ndarray (n_y, n_x)
        Elevation surface, metres, sampled on the ``(y, x)`` meshgrid
        implied by *x*/*y* — the same row-major convention
        ``numpy.meshgrid(x, y)`` (default ``indexing="xy"``) produces.

    Examples
    --------
    >>> import numpy as np
    >>> from pcsf.core.schema import TopographyRaster
    >>> topo = TopographyRaster(x=[0.0, 10.0, 20.0], y=[0.0, 10.0],
    ...                         elevation=np.zeros((2, 3)))
    >>> topo.validate()
    """

    kind: ClassVar[str] = "raster"

    x: np.ndarray
    y: np.ndarray
    elevation: np.ndarray

    def __post_init__(self) -> None:
        self.x = _arr(self.x)
        self.y = _arr(self.y)
        self.elevation = _arr(self.elevation)

    def validate(self) -> None:
        """Check the consistency of the arrays.

        Raises
        ------
        GeometryError
            If *x* or *y* is not 1-D or *elevation* does not
            have shape ``(len(y), len(x))``.
        """
        if self.x.ndim != 1 or self.y.ndim != 1:
            raise GeometryError(
                "TopographyRaster.x and .y must be 1-D"
            )
        expected = (self.y.shape[0], self.x.shape[0])
        if self.elevation.shape != expected:
            raise GeometryError(
                "TopographyRaster.elevation shape "
                f"{self.elevation.shape} "
                f"does not match (len(y), len(x)) = {expected}"
            )


# ---------------------------------------------------------------------
# Root container
# ---------------------------------------------------------------------


@dataclass(repr=False)
class PCSFModel(PCSFObject, MetadataMixin):
    """Solver-neutral resistivity model; one PCSF file.

    Parameters
    ----------
    geometry : Grid2DGeometry, Grid3DGeometry,
            UnstructuredMeshGeometry or MultilineGeometry
        The model's geometry, discriminated by ``geometry.kind``.
    resistivity : ndarray, optional
        Canonical **linear ohm.m** resistivity. Required for
        ``grid2d``/``grid3d``/``mesh_unstructured`` geometries;
        must be ``None`` for ``multiline`` (each line carries its own
        resistivity — see :class:`LineEntry`).
    resistivity_native : ndarray, optional
        Passthrough of the source backend's own array, for provenance.
    resistivity_native_encoding : str, optional
        Encoding of *resistivity_native*, a name from
        :func:`pcsf.core.encodings.known_encodings`. Required
        whenever *resistivity_native* is given; never assumed.
    uncertainty, sensitivity : ndarray, optional
        Same shape as *resistivity*, when available from the source.
    resistivity_by_region : ndarray, optional
        Per-region resistivity table (``mesh_unstructured`` only),
        alongside the per-cell *resistivity* expanded from it.
    resistivity_by_node : ndarray, optional
        Per-node resistivity table (``mesh_unstructured`` only), shape
        ``(n_nodes,)`` -- the natural output shape of a graph-based
        model (e.g. a GCN) that predicts one value per mesh vertex
        rather than per cell. Kept alongside the per-cell
        *resistivity* derived from it (see
        :func:`pcsf.algorithms.node_to_cell`).
    stations : StationTable, optional
    topography : TopographyPerStation | TopographyRaster, optional
    survey : dict
        Free-form survey metadata. Adapters populate this from
        survey-metadata objects (``SurveyMeta``, ``BBox``,
        ``ProvenanceMeta``) via their own dict conversion; PCSF itself
        does not require a specific metadata class here.
    history : dict of ndarray
        Optional per-iteration series (e.g. ``{"rms": ..., "lambda":
        ...}``) from an ``InversionHistory``-like source.
    source_backend : str, default "generic"
        ``"occam2d"`` | ``"modem3d"`` | ``"mare2dem"`` | ``"duhi"`` |
        ``"generic"``.
    created_by, created_at : str
        Producing software and ISO 8601 creation time.
    crs : str, optional
        A pyproj-compatible CRS string.
    description : str
        Free text.
    metadata : dict
        Free-form metadata, including the inversion record
        (``metadata["inversion"]``).
    boreholes : dict or object, optional
        Borehole association, interpreted by the borehole
        companion format and stored as JSON.

    See Also
    --------
    pcsf.read, pcsf.write, pcsf.validate

    Notes
    -----
    Arrays are converted to ``float64`` on construction but
    not checked; call :meth:`validate` (the writers do) to
    check shapes and encodings.

    Examples
    --------
    >>> import numpy as np
    >>> import pcsf
    >>> native = np.log10([[100.0, 300.0]])
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0, 10.0], z=[5.0]),
    ...     resistivity=10.0**native,
    ...     resistivity_native=native,
    ...     resistivity_native_encoding="log10",
    ...     source_backend="occam2d",
    ... )
    >>> model.validate()
    >>> model.kind
    'grid2d'
    """

    geometry: (
        Grid2DGeometry
        | Grid3DGeometry
        | UnstructuredMeshGeometry
        | MultilineGeometry
    )
    resistivity: np.ndarray | None = None
    resistivity_native: np.ndarray | None = None
    resistivity_native_encoding: str | None = None
    uncertainty: np.ndarray | None = None
    sensitivity: np.ndarray | None = None
    resistivity_by_region: np.ndarray | None = None
    resistivity_by_node: np.ndarray | None = None
    stations: StationTable | None = None
    topography: TopographyPerStation | TopographyRaster | None = None
    survey: dict[str, Any] = field(default_factory=dict)
    history: dict[str, np.ndarray] = field(default_factory=dict)
    source_backend: str = "generic"
    created_by: str = ""
    created_at: str = ""
    crs: str | None = None
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    boreholes: Any | None = None

    def __post_init__(self) -> None:
        self.resistivity = _opt_arr(self.resistivity)
        self.resistivity_native = _opt_arr(self.resistivity_native)
        self.uncertainty = _opt_arr(self.uncertainty)
        self.sensitivity = _opt_arr(self.sensitivity)
        self.resistivity_by_region = _opt_arr(
            self.resistivity_by_region
        )
        self.resistivity_by_node = _opt_arr(self.resistivity_by_node)
        self.history = {
            str(key): _arr(value)
            for key, value in dict(self.history).items()
        }

    @property
    def kind(self) -> str:
        """Geometry kind, such as ``"grid2d"``."""
        return self.geometry.kind

    def validate(self) -> None:
        """Check the consistency of the arrays.

        Raises
        ------
        GeometryError
            If the geometry is invalid or an array shape does
            not match it.
        EncodingError
            If source values are given without a known
            encoding.
        TypeError
            If *boreholes* is neither a dict nor an object
            with ``to_dict()``.
        """
        kind = self.geometry.kind
        if kind not in GEOMETRY_KINDS:
            raise GeometryError(
                f"unknown geometry kind {kind!r}; expected one of "
                f"{GEOMETRY_KINDS}"
            )
        self.geometry.validate()

        if kind == "multiline":
            if self.resistivity is not None:
                raise GeometryError(
                    "multiline geometry carries resistivity per line "
                    "(PCSFModel.resistivity must be None); set it on "
                    "each LineEntry instead"
                )
        else:
            if self.resistivity is None:
                raise GeometryError(
                    "resistivity is required for geometry "
                    f"kind {kind!r}"
                )
            if kind == "mesh_unstructured":
                # Per-cell (m,) or the region-collapsed (n_regions,)
                # form.
                valid_shapes = {
                    (self.geometry.connectivity.shape[0],),
                    (self.geometry.n_regions,),
                }
                if self.resistivity.shape not in valid_shapes:
                    raise GeometryError(
                        "resistivity shape "
                        f"{self.resistivity.shape} does "
                        "not match mesh cells or region "
                        f"count {valid_shapes}"
                    )
            else:
                expected = self.geometry.resistivity_shape
                if self.resistivity.shape != expected:
                    raise GeometryError(
                        "resistivity shape "
                        f"{self.resistivity.shape} does "
                        f"not match geometry {expected}"
                    )
            for label, arr in (
                ("uncertainty", self.uncertainty),
                ("sensitivity", self.sensitivity),
            ):
                if (
                    arr is not None
                    and arr.shape != self.resistivity.shape
                ):
                    raise GeometryError(
                        f"{label} shape {arr.shape} does not match "
                        f"resistivity shape {self.resistivity.shape}"
                    )

        if self.resistivity_by_node is not None:
            if kind != "mesh_unstructured":
                raise GeometryError(
                    "resistivity_by_node is only valid for "
                    "geometry kind 'mesh_unstructured', "
                    f"got {kind!r}"
                )
            n_nodes = self.geometry.nodes.shape[0]
            if self.resistivity_by_node.shape != (n_nodes,):
                raise GeometryError(
                    "resistivity_by_node shape "
                    f"{self.resistivity_by_node.shape} does not match "
                    f"the mesh's node count ({n_nodes},)"
                )

        if (
            self.resistivity_native is not None
            and not is_known_encoding(self.resistivity_native_encoding)
        ):
            raise EncodingError(
                "resistivity_native_encoding must be one of "
                f"{known_encodings()} when resistivity_native is set, "
                f"got {self.resistivity_native_encoding!r}"
            )

        if self.stations is not None:
            self.stations.validate()
        if self.topography is not None:
            self.topography.validate()
        if self.boreholes is not None:
            # The borehole association is interpreted by the borehole
            # companion format (a plugin); the core accepts a JSON-like
            # dict or any object with to_dict(), and validates it if it
            # can.
            if not isinstance(self.boreholes, dict) and not callable(
                getattr(self.boreholes, "to_dict", None)
            ):
                raise TypeError(
                    "boreholes must be a dict or provide to_dict()"
                )
            validate = getattr(self.boreholes, "validate", None)
            if callable(validate):
                validate()
