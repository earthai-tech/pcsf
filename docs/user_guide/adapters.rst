Solver adapters
===============

An adapter reads the native files of an inversion code and returns
a :class:`~pcsf.PCSFModel` in the geometry of that code. The
adapters need no inversion package: the native files are parsed by
:mod:`pcsf.native` with NumPy only.

.. list-table::
   :header-rows: 1
   :widths: 18 34 24 24

   * - Solver
     - Adapter
     - Geometry kind
     - Extra
   * - Occam2D
     - :func:`~pcsf.adapters.occam2d_to_pcsf`
     - ``grid2d``
     -
   * - ModEM
     - :func:`~pcsf.adapters.modem_to_pcsf`
     - ``grid3d``
     -
   * - MARE2DEM
     - :func:`~pcsf.adapters.mare2dem_to_pcsf`
     - ``mesh_unstructured``
     - ``mare2dem``
   * - EMC netCDF
     - :func:`~pcsf.adapters.emc_to_pcsf`,
       :func:`~pcsf.adapters.pcsf_to_emc`
     - ``grid3d``
     - ``emc``

Each adapter keeps the source values and their encoding, builds the
station table when the run has a data file, and attaches the
:doc:`inversion record <inversion_record>` it can read from the
logs.

Occam2D
-------

The adapter takes the folder of a run and reads its last iteration,
or the one given by ``iteration``:

.. doctest::

   >>> from pcsf.adapters import occam2d_to_pcsf
   >>> model = occam2d_to_pcsf(pcsf.datasets.path("occam2d_tiny"))
   >>> model.kind, model.source_backend
   ('grid2d', 'occam2d')
   >>> len(model.stations.name)
   3

ModEM
-----

The adapter takes the ``.rho`` model file, and optionally the data
file (for the stations) and the log (for the inversion record):

.. doctest::

   >>> from pcsf.adapters import modem_to_pcsf
   >>> run = pcsf.datasets.path("modem_tiny")
   >>> rho = sorted(run.glob("*.rho"))[-1]
   >>> data = sorted(run.glob("*.dat"))[0]
   >>> model = modem_to_pcsf(rho, data=data,
   ...                       station_z_convention="elevation")
   >>> model.kind, model.resistivity_native_encoding
   ('grid3d', 'ln')
   >>> len(model.stations.name)
   2

Two conventions of ModEM files are resolved explicitly:

- **Air cells.** Cells above ``air_threshold_ohm_m``
  (:math:`10^{8}` ohm m by default) are treated as air and set to
  NaN in the canonical values; ``None`` keeps them.
- **Station Z.** The ``Z`` column of a data file is an elevation in
  some files and a depth in others. ``station_z_convention`` states
  which (``"elevation"`` or ``"depth_down"``); with ``"auto"`` the
  adapter decides from the file, and warns when it reads the
  column as a depth and converts it to elevation.

MARE2DEM
--------

The adapter takes a ``.N.resistivity`` file. The triangulation
comes from the ``.poly`` file next to it, which needs the
``mare2dem`` extra, or from a mesh passed as ``mesh``. Region
numbers, which start at 1 in MARE2DEM, become 0-based
``region_ids``.

EMC netCDF
----------

:func:`~pcsf.adapters.emc_to_pcsf` reads a model of the EarthScope
/ IRIS Earth Model Collaboration and
:func:`~pcsf.adapters.pcsf_to_emc` writes it back. Both need the
``emc`` extra.

Other solvers
-------------

A package registers an adapter for another solver through the
``pcsf.adapters`` entry-point group; see
:doc:`../developer/plugins`.
