Resistivity encodings
=====================

Solvers store resistivity in different forms: its decimal or
natural logarithm, its linear value, or conductivity. Reading
:math:`\ln\rho` as :math:`\log_{10}\rho` changes a model by a
factor of 2.3 in the exponent, which is why a file states the
form explicitly.

A model keeps two arrays:

- ``resistivity``, the **canonical** values, always linear
  resistivity :math:`\rho` in ohm m;
- ``resistivity_native``, the **source** values exactly as the
  solver wrote them, with ``resistivity_native_encoding`` naming
  their form.

Rule ``C5.native`` checks that the two agree.

Built-in encodings
------------------

With :math:`v` the source value, :math:`\rho` the resistivity in
ohm m and :math:`\sigma = 1/\rho` the conductivity in S/m:

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Name
     - Source value
     - Resistivity
   * - ``linear``
     - :math:`v = \rho`
     - :math:`\rho = v`
   * - ``log10``
     - :math:`v = \log_{10}\rho`
     - :math:`\rho = 10^{v}`
   * - ``ln``
     - :math:`v = \ln\rho`
     - :math:`\rho = e^{v}`
   * - ``conductivity``
     - :math:`v = \sigma`
     - :math:`\rho = 1/v`
   * - ``log10_conductivity``
     - :math:`v = \log_{10}\sigma`
     - :math:`\rho = 10^{-v}`

.. doctest::

   >>> from pcsf.core.encodings import (
   ...     from_resistivity, known_encodings, to_resistivity)
   >>> known_encodings()
   ('conductivity', 'linear', 'ln', 'log10', 'log10_conductivity')
   >>> to_resistivity([2.0, 3.0], "log10")
   array([ 100., 1000.])
   >>> from_resistivity([100.0], "log10_conductivity")
   array([-2.])

Other encodings
---------------

A package adds an encoding by registering the conversion and its
inverse; files then declare its name, and every reader with the
package installed converts them. See
:doc:`../developer/plugins`.

Uncertainty
-----------

A standard deviation given in one encoding is not the standard
deviation in another. The functions of
:mod:`pcsf.algorithms` convert it
(:func:`~pcsf.algorithms.log_uncertainty`,
:func:`~pcsf.algorithms.transform_covariance`,
:func:`~pcsf.algorithms.lognormal_relative_std`); see
:doc:`algorithms`.
