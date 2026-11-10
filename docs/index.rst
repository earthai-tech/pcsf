pcsf: Portable Common Subsurface Format
=======================================

**pcsf** is an exchange format for electromagnetic and
magnetotelluric inversion models, with the tools and algorithms to
read, write, validate, sample and compare them.

Every inversion code writes its own format, with its own logarithm
base, axis order, coordinate frame, depth datum and discretization.
A reader who does not know these conventions misreads the model, and
the errors are of the same size as the geological contrasts the
model is meant to show. PCSF states them in the file:

- **canonical resistivity** in linear ohm m, with the source values
  and their encoding kept unchanged;
- **native geometry**: 2D section, 3D grid, triangular mesh or set
  of profiles, never resampled;
- **spatial reference**: station table, topography, coordinate
  reference system;
- **inversion record**: data, errors, solver, regularization,
  misfit, convergence and depth of investigation, with a
  completeness check.

One model has two encodings that convert into each other without
loss: **PCSF** (HDF5, binary, compressed) and **PCSM** (plain text,
optionally ``.pcsm.gz``).

.. code-block:: python

   import pcsf

   model = pcsf.read("model.pcsf")
   pcsf.validate(model).raise_if_failed()
   pcsf.write(model, "model.pcsm.gz")

This documentation describes package version |release| and format
version |format_version|.

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   getting_started/index

.. toctree::
   :maxdepth: 2
   :caption: User guide

   user_guide/index

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api/index
   specification
   changelog

.. toctree::
   :maxdepth: 2
   :caption: Development

   developer/index

Citing
------

The format and its algorithms are described in a manuscript in
preparation for *Geophysics*. Until it is published, cite the
software with the metadata of ``CITATION.cff`` in the repository.

Licence
-------

BSD 3-Clause.
