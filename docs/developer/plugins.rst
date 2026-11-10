Plugins
=======

Other packages extend pcsf through three entry-point groups. Each
entry point names a callable that registers something when pcsf
loads its plugins (:func:`pcsf.plugins.load_plugins`).

.. list-table::
   :header-rows: 1
   :widths: 26 34 40

   * - Group
     - Registers
     - With
   * - ``pcsf.encodings``
     - resistivity encodings
     - :func:`~pcsf.api.registry.register_encoding`
   * - ``pcsf.adapters``
     - native-to-PCSF adapters
     - :func:`~pcsf.api.registry.register_adapter`
   * - ``pcsf.formats``
     - companion formats (boreholes, geology)
     - :func:`~pcsf.api.registry.register_format`

Adding an encoding
------------------

An encoding is a conversion from source values to linear
resistivity, and its inverse:

.. code-block:: python

   # my_package/pcsf_plugin.py
   import numpy as np
   from pcsf.api.registry import register_encoding


   def register_encodings():
       @register_encoding(
           "log10_conductance",
           inverse=lambda rho: -np.log10(rho),
           quantity="conductivity",
           description="log10 of S",
       )
       def _to_rho(values):
           return 10.0 ** (-values)

.. code-block:: toml

   # my_package/pyproject.toml
   [project.entry-points."pcsf.encodings"]
   my_encodings = "my_package.pcsf_plugin:register_encodings"

Files then declare ``log10_conductance`` as their encoding, and
every reader with the package installed converts them.

Adding a solver adapter
-----------------------

Write a parser of the native files that uses NumPy only and
returns plain arrays, then an adapter that builds a
:class:`~pcsf.PCSFModel`, attaches the inversion record, and
registers itself with
:func:`~pcsf.api.registry.register_adapter`. Inside pcsf, parsers
live in ``pcsf/native/`` and adapters in ``pcsf/adapters/``; add a
small real example to ``conformance/files/`` with its expected
values.

Adding a companion format
-------------------------

Boreholes, geology legends and other companion formats are
separate packages. They register a descriptor with
:func:`~pcsf.api.registry.register_format` through the
``pcsf.formats`` group, and pcsf hands them the groups of a file
it does not decode itself.
