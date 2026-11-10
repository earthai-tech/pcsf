Conformance
===========

The specification states rules that every file must satisfy. Each
has an identifier, so that reports can be compared between
implementations.

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Rule
     - Requirement
   * - ``C1.kind``
     - the geometry kind is one of the specified kinds
   * - ``C2.positive``
     - resistivity is positive where defined
   * - ``C3.shape``
     - the shape of the resistivity matches the geometry
   * - ``C4.encoding``
     - source values declare a known encoding
   * - ``C5.native``
     - source values reproduce the canonical values
   * - ``C6.multiline_root``
     - a ``multiline`` model has no resistivity at its root
   * - ``C7.synthesized``
     - a derived volume is labelled synthesized
   * - ``C8.lonlat``
     - station longitude and latitude come together
   * - ``C9.uncertainty``
     - uncertainty and sensitivity have the shape of the
       resistivity
   * - ``C10.regions``
     - mesh region indices are 0-based and within the region table

Only the rules that apply to a model are evaluated: ``C10.regions``
for meshes, ``C6`` and ``C7`` for ``multiline`` models, and so on.

Checking a model
----------------

:func:`pcsf.validate` takes a model or a path and returns a
:class:`~pcsf.core.conformance.ConformanceReport`:

.. doctest::

   >>> from pcsf.adapters import occam2d_to_pcsf
   >>> model = occam2d_to_pcsf(pcsf.datasets.path("occam2d_tiny"))
   >>> report = pcsf.validate(model)
   >>> report.passed
   True
   >>> [r.rule for r in report.results]
   ['C1.kind', 'C3.shape', 'C2.positive', 'C4.encoding', 'C5.native', 'C8.lonlat']
   >>> print(str(report).splitlines()[-1])
   6/6 rules passed

A model that breaks a rule is reported, not rejected:

.. doctest::

   >>> model.resistivity[0, 0] = -1.0
   >>> report = pcsf.validate(model)
   >>> report.passed
   False
   >>> [r.rule for r in report.failures]
   ['C2.positive']
   >>> report.raise_if_failed()
   Traceback (most recent call last):
   ...
   pcsf.exceptions.ConformanceError: ...

From the command line, ``pcsf validate`` prints the report of each
file.

Conformance suite
-----------------

The folder ``conformance/`` of the repository holds reference files
and the values an independent implementation must read from them.
A reader written in another language is checked against the same
files and the same rule identifiers.
