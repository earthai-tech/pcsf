Installation
============

pcsf needs Python 3.9 or later. The core depends on NumPy and h5py
only; everything else is optional and installed through *extras*.

From PyPI
---------

.. code-block:: bash

   pip install pcsf

.. note::

   Until the first release is on PyPI, install from the repository
   (see `From source`_).

Optional features
-----------------

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Extra
     - Installs
     - Needed for
   * - ``algorithms``
     - SciPy, matplotlib
     - sampling, registration and comparison helpers that use them
   * - ``emc``
     - netCDF4
     - EarthScope / IRIS Earth Model Collaboration (EMC) archives
   * - ``mare2dem``
     - triangle
     - triangulation of MARE2DEM models
   * - ``schema``
     - jsonschema
     - validation of the metadata against the JSON Schemas
   * - ``geo``
     - pyproj
     - coordinate reference systems
   * - ``studio``
     - PySide6, matplotlib
     - :doc:`PCSF Studio <../studio/index>`, the graphical
       viewer
   * - ``all``
     - all of the above
     -

Several extras are combined with commas:

.. code-block:: bash

   pip install "pcsf[emc,mare2dem]"
   pip install "pcsf[all]"

A function that needs a missing optional package raises
:class:`~pcsf.MissingDependencyError`, whose message names the
extra to install.

From source
-----------

.. code-block:: bash

   git clone https://github.com/earthai-tech/pcsf
   cd pcsf
   pip install -e ".[dev]"
   pytest

The ``dev`` extra adds the test and lint tools, ``docs`` the
documentation tools (see :doc:`../developer/contributing`).

PCSF Studio without Python
--------------------------

Installers of PCSF Studio that need no Python (Windows ``setup.exe``,
Linux AppImage and self-extracting ``.sh``) are attached to each
release on GitHub.

Checking the installation
-------------------------

.. code-block:: bash

   pcsf version
   pcsf-studio --self-test      # with the studio extra
