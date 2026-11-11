Quick start
===========

The examples of this page run as written; the package ships three
small solver runs in :mod:`pcsf.datasets` so that no data file is
needed.

Convert a solver result
-----------------------

A model starts in the format of the code that inverted it. An
*adapter* reads the native files and returns a
:class:`~pcsf.PCSFModel`:

.. doctest::

   >>> import pcsf
   >>> from pcsf.adapters import occam2d_to_pcsf
   >>> run = pcsf.datasets.path("occam2d_tiny")
   >>> model = occam2d_to_pcsf(run)
   >>> model.kind
   'grid2d'
   >>> model.resistivity.shape
   (4, 8)

:func:`pcsf.info` gives a short description:

.. doctest::

   >>> summary = pcsf.info(model)
   >>> summary["source_backend"], summary["native_encoding"]
   ('occam2d', 'log10')
   >>> summary["n_cells"], summary["n_stations"]
   (32, 3)

``model.resistivity`` is always linear resistivity in ohm m. The
values the solver wrote (here :math:`\log_{10}\rho`) are kept next
to it, unchanged, in ``model.resistivity_native``.

Write and read
--------------

:func:`pcsf.write` chooses the encoding from the suffix and
:func:`pcsf.read` detects it from the content:

.. doctest::

   >>> path = pcsf.write(model, "model.pcsf")
   >>> text = pcsf.write(model, "model.pcsm.gz")
   >>> pcsf.detect(path), pcsf.detect(text)
   ('pcsf', 'pcsm.gz')
   >>> back = pcsf.read(text)
   >>> import numpy as np
   >>> bool(np.array_equal(back.resistivity, model.resistivity,
   ...                     equal_nan=True))
   True

The comparison allows NaN: cells without a value are stored as
NaN and come back as NaN.

Validate
--------

:func:`pcsf.validate` checks the conformance rules of the
specification on a model or on a file:

.. doctest::

   >>> report = pcsf.validate("model.pcsf")
   >>> report.passed
   True
   >>> report.raise_if_failed()

Sample a model
--------------

:func:`~pcsf.algorithms.sample_log10` evaluates
:math:`\log_{10}\rho` at arbitrary points, given as ``(x, z)`` for a
section:

.. doctest::

   >>> from pcsf.algorithms import sample_log10
   >>> g = model.geometry
   >>> points = np.array([[g.x[2], g.z[1]], [g.x[5], g.z[2]]])
   >>> values = sample_log10(model, points)
   >>> values.shape
   (2,)
   >>> expected = np.log10(model.resistivity[[1, 2], [2, 5]])
   >>> bool(np.allclose(values, expected))
   True

Build a model by hand
---------------------

A model is a geometry and an array of resistivity:

.. doctest::

   >>> rho = np.array([[100.0, 300.0, 1000.0],
   ...                 [50.0, 200.0, 800.0]])
   >>> model = pcsf.PCSFModel(
   ...     geometry=pcsf.Grid2DGeometry(
   ...         x=[0.0, 100.0, 200.0], z=[25.0, 75.0]
   ...     ),
   ...     resistivity=rho,
   ...     resistivity_native=np.log10(rho),
   ...     resistivity_native_encoding="log10",
   ...     source_backend="example",
   ... )
   >>> pcsf.validate(model).passed
   True

Next steps
----------

- :doc:`../user_guide/data_model` describes the model and its four
  geometry kinds.
- :doc:`../user_guide/adapters` lists the supported solvers.
- :doc:`cli` does the same from a terminal.
- :doc:`../studio/index` opens models in a window.
