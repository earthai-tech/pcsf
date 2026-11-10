Data model
==========

A file holds one :class:`~pcsf.PCSFModel`: a geometry, the
resistivity of its cells, and what is needed to place and judge
the model.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Attribute
     - Content
   * - ``geometry``
     - one of the four geometry kinds below
   * - ``resistivity``
     - canonical values, linear resistivity in ohm m
   * - ``resistivity_native``, ``resistivity_native_encoding``
     - the values the solver wrote and their encoding
       (:doc:`encodings`)
   * - ``uncertainty``, ``sensitivity``
     - optional arrays of the shape of ``resistivity``
   * - ``stations``
     - :class:`~pcsf.StationTable`: names, model-frame
       coordinates, optional longitude and latitude
   * - ``topography``
     - :class:`~pcsf.TopographyPerStation` or
       :class:`~pcsf.TopographyRaster`
   * - ``crs``
     - coordinate reference system of the model frame
   * - ``metadata``
     - free metadata, including the
       :doc:`inversion record <inversion_record>`
   * - ``source_backend``, ``created_by``, ``created_at``,
       ``description``
     - where the model comes from

Coordinates are in metres. Depth is positive downward.

Geometry kinds
--------------

The geometry is stored as the solver discretized it. A model is
never resampled on reading or writing; resampling is an explicit
operation of :doc:`algorithms`.

.. list-table::
   :header-rows: 1
   :widths: 22 30 24 24

   * - ``model.kind``
     - Class
     - Shape of ``resistivity``
     - Typical source
   * - ``grid2d``
     - :class:`~pcsf.Grid2DGeometry`
     - ``(n_z, n_x)``
     - Occam2D
   * - ``grid3d``
     - :class:`~pcsf.Grid3DGeometry`
     - ``(n_z, n_y, n_x)``
     - ModEM, EMC
   * - ``mesh_unstructured``
     - :class:`~pcsf.UnstructuredMeshGeometry`
     - ``(n_triangles,)`` or ``(n_regions,)``
     - MARE2DEM
   * - ``multiline``
     - :class:`~pcsf.MultilineGeometry`
     - one ``(n_z, n_x)`` array per line
     - several 2D profiles

``grid2d`` and ``grid3d``
~~~~~~~~~~~~~~~~~~~~~~~~~

``x``, ``y`` and ``z`` are cell centres; ``x_nodes``, ``y_nodes``
and ``z_nodes`` are the optional cell edges, one more than the
centres. ``origin`` places a locally referenced grid in the frame
of the station table. The axis order of a ``grid3d`` array,
``(n_z, n_y, n_x)``, is the one of ModEM.

.. doctest::

   >>> from pcsf.adapters import modem_to_pcsf
   >>> run = pcsf.datasets.path("modem_tiny")
   >>> rho = sorted(run.glob("*.rho"))[-1]
   >>> model = modem_to_pcsf(rho)
   >>> model.kind, model.resistivity.shape
   ('grid3d', (3, 4, 5))
   >>> g = model.geometry
   >>> len(g.z), len(g.y), len(g.x)
   (3, 4, 5)

``mesh_unstructured``
~~~~~~~~~~~~~~~~~~~~~

``nodes`` are the node coordinates, ``connectivity`` the three node
indices of each triangle, and ``region_ids`` the 0-based index of
the region of each triangle. The resistivity is given per triangle
or per region; a reader checks which by its length. ``plane`` names
the physical plane (``"xz"`` by default).

``multiline``
~~~~~~~~~~~~~

A set of 2D profiles with their real positions. Each
:class:`~pcsf.LineEntry` carries its own ``grid2d`` geometry and
resistivity, and the model has no resistivity at its root. An
optional :class:`~pcsf.DerivedVolume` interpolated between the
lines is always labelled as synthesized, so that it is never taken
for a 3D inversion.

Stations and topography
-----------------------

The station table is shared by every geometry kind. ``x``, ``y``
and ``z`` are in the model frame; ``lon`` and ``lat``, when given,
come together (rule ``C8.lonlat``). ``line_id`` assigns stations to
the lines of a ``multiline`` model.

Topography is either the elevation of each station
(:class:`~pcsf.TopographyPerStation`) or a gridded surface
independent of the stations (:class:`~pcsf.TopographyRaster`).

See also
--------

The :doc:`specification <../specification>` gives the layout of
each kind in the file.
