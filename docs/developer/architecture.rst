Architecture
============

Layout
------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Package
     - Content
   * - :mod:`pcsf.api`
     - **stable public API**: the facade (``read``, ``write``,
       ``convert``, ``detect``, ``validate``, ``info``), base
       classes, types and registries
   * - ``pcsf.core``
     - data model, encodings, versioning, HDF5 and text I/O,
       inversion record, conformance
   * - :mod:`pcsf.algorithms`
     - sampling, point location, comparison, uncertainty,
       projection, registration
   * - :mod:`pcsf.native`, :mod:`pcsf.adapters`
     - parsers of solver files and converters to models
   * - :mod:`pcsf.plugins`
     - discovery of entry points
   * - ``pcsf.cli``, :mod:`pcsf.studio`
     - command-line tool and graphical application
   * - ``pcsf.utils``, ``pcsf.compat``
     - shared helpers; version and optional-dependency shims
   * - :mod:`pcsf.exceptions`, :mod:`pcsf.decorators`
     - error hierarchy and shared decorators

The repository also holds ``spec/`` (the specification and the
PCSM grammar), ``conformance/`` (reference files and expected
values), ``installers/`` (PCSF Studio builds) and ``paper/``
(reproduction of the manuscript).

Rules
-----

- **Public and internal.** Everything under :mod:`pcsf.api`, and
  re-exported by :mod:`pcsf`, follows semantic versioning. Other
  modules are internal and may change between minor versions.
- **Dependencies.** The core needs NumPy and h5py only. Any other
  package is optional, imported through
  :func:`pcsf.compat.import_optional` or the
  :func:`~pcsf.decorators.requires` decorator, and listed in an
  extra.
- **Independence.** pcsf imports no inversion package. Packages
  that use the format depend on pcsf, not the reverse.
- **Errors.** Functions raise subclasses of
  :class:`~pcsf.PCSFError`.
- **Version differences** of Python, NumPy and h5py are handled in
  ``pcsf.compat`` only.

Two versions
------------

The package version and the format version are independent. The
format version is written in every file; a minor format version
adds optional fields, kinds or encodings and stays readable by
older readers, and a major version changes existing fields.

PCSF Studio
-----------

The Studio is split in a part without Qt
(:mod:`pcsf.studio.sources`, :mod:`pcsf.studio.figures`,
:mod:`pcsf.studio.summary`, :mod:`pcsf.studio.style`), tested on
its own, and thin Qt widgets (:mod:`pcsf.studio.window`) that hold
no format logic.
