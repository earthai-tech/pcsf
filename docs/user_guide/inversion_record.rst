Inversion record
================

A resistivity model cannot be judged without knowing how it was
obtained. The :class:`~pcsf.InversionRecord` stores this next to
the model, in ``model.metadata["inversion"]``, and a completeness
check lists what is missing.

Content
-------

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Group
     - Fields
   * - ``solver``, ``solver_version``
     - the inversion code
   * - ``data``
     - ``components``, ``frequency_range_hz``, ``n_stations``,
       ``n_frequencies``, ``errors``, ``sign_convention``,
       ``source``
   * - ``forward``
     - ``dimensionality``, ``mesh``
   * - ``regularization``
     - ``type``, ``trade_off``, ``start_model``
   * - ``misfit``
     - ``final_rms``, ``target_rms``, ``n_iterations``,
       ``termination``
   * - ``reliability``
     - ``method``, ``depth_of_investigation_m``
   * - ``citation``
     - ``authors``, ``year``, ``licence``

``misfit.termination`` is one of ``target_reached``,
``iteration_limit``, ``time_limit``, ``stalled`` or ``unknown``.

Required and recommended fields
-------------------------------

The **required** fields are those without which a model cannot be
interpreted: ``solver``, ``data.components``,
``data.frequency_range_hz``, ``data.n_stations``, ``data.errors``,
``regularization.type``, ``misfit.final_rms`` and
``misfit.termination``. The other fields of the table are
**recommended**.

.. doctest::

   >>> record = pcsf.InversionRecord(
   ...     solver="occam2d",
   ...     data={"components": ["TE", "TM"], "n_stations": 12},
   ...     misfit={"final_rms": 1.04,
   ...             "termination": "target_reached"},
   ... )
   >>> missing = pcsf.check_inversion_record(record)
   >>> missing["required"]
   ['data.frequency_range_hz', 'data.errors', 'regularization.type']

Attaching and reading
---------------------

.. doctest::

   >>> from pcsf.adapters import occam2d_to_pcsf
   >>> model = occam2d_to_pcsf(pcsf.datasets.path("occam2d_tiny"))
   >>> model = pcsf.attach_inversion_record(model, record)
   >>> pcsf.get_inversion_record(model).solver
   'occam2d'

:func:`pcsf.get_inversion_record` returns ``None`` for a model
without a record. The adapters fill the fields they can read from
the solver logs; the rest is for the author of the model to add.

Models from machine learning
----------------------------

A model produced by a trained network is described by a
:class:`~pcsf.ModelProvenance`: architecture, framework,
checkpoint and its SHA-256, training data, hyperparameters and
random seed.
