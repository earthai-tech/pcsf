Algorithms
==========

:mod:`pcsf.algorithms` computes with models without leaving their
native geometry. The algorithms use NumPy only.

Sampling
--------

:func:`~pcsf.algorithms.sample_log10` evaluates
:math:`\log_{10}\rho` at arbitrary points: multilinear
interpolation between cell centres on grids, the value of the
containing triangle on meshes.

.. doctest::

   >>> from pcsf.adapters import occam2d_to_pcsf
   >>> from pcsf.algorithms import sample_log10
   >>> model = occam2d_to_pcsf(pcsf.datasets.path("occam2d_tiny"))
   >>> g = model.geometry
   >>> centre = np.array([[g.x[3], g.z[1]]])
   >>> value = sample_log10(model, centre)
   >>> bool(np.isclose(value[0], np.log10(model.resistivity[1, 3])))
   True

Interpolation is done on :math:`\log_{10}\rho`, in which
resistivity varies smoothly, not on :math:`\rho`.

The weights are available on their own
(:func:`~pcsf.algorithms.interpolation_weights`). With
:math:`w_k` the weight of cell :math:`k` and :math:`m_k` its
value, the sampled value is

.. math::

   m(\mathbf{p}) = \sum_k w_k(\mathbf{p})\, m_k ,
   \qquad \sum_k w_k = 1 ,

so that the same weights propagate uncertainty
(:func:`~pcsf.algorithms.interpolated_std`).

Point location in meshes
------------------------

:func:`~pcsf.algorithms.locate_triangles` returns the triangle
containing each point. For repeated queries on one mesh,
:class:`~pcsf.algorithms.TriangleLocator` builds its search
structure once.

Comparison
----------

:func:`~pcsf.algorithms.compare_log10` compares two fields of
:math:`\log_{10}\rho` sampled at the same points and returns a
:class:`~pcsf.algorithms.ComparisonResult` with the difference
field and its statistics. With :math:`\delta_i = a_i - b_i` over
the :math:`n` points where both are defined:

.. math::

   \mathrm{bias} = \frac{1}{n}\sum_i \delta_i , \qquad
   \mathrm{rms} = \sqrt{\frac{1}{n}\sum_i \delta_i^2} .

.. doctest::

   >>> from pcsf.algorithms import compare_log10
   >>> a = np.log10(model.resistivity)
   >>> result = compare_log10(a, a + 0.1)
   >>> round(result.bias, 3), round(result.rms, 3), result.n
   (-0.1, 0.1, 24)

Of the 32 cells of this section, 8 have no value; ``n`` counts the
24 that enter the statistics.

Two models on different discretizations are compared by sampling
both at common points first.

Uncertainty
-----------

.. list-table::
   :header-rows: 1
   :widths: 44 56

   * - Function
     - Does
   * - :func:`~pcsf.algorithms.log_uncertainty`
     - converts a standard deviation between encodings
   * - :func:`~pcsf.algorithms.encoding_jacobian`
     - derivative of one encoding with respect to another, per
       cell
   * - :func:`~pcsf.algorithms.transform_covariance`
     - transforms a covariance matrix to another encoding
   * - :func:`~pcsf.algorithms.lognormal_relative_std`
     - exact relative standard deviation of a log-normal
       resistivity
   * - :func:`~pcsf.algorithms.interpolated_std`
     - standard deviation of interpolated values

Meshes and grids
----------------

- :func:`~pcsf.algorithms.node_to_cell` turns per-node values into
  per-triangle values, with a geometric mean by default.
- :func:`~pcsf.algorithms.mesh_to_grid2d` samples a triangular-mesh
  model on a regular ``grid2d``; the result is a new model, and the
  mesh model is unchanged.

Coordinate frames
-----------------

:func:`~pcsf.algorithms.register_frame` estimates the affine map
between projected coordinates and the model frame from points
known in both, and :func:`~pcsf.algorithms.decompose_frame` splits
it into axis permutation, rotation and scales. This finds swapped
or mirrored axes before they are plotted.
