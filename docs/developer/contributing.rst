Contributing
============

The full guide is ``CONTRIBUTING.md`` at the root of the
repository. This page gives the commands.

Set-up
------

.. code-block:: bash

   git clone https://github.com/earthai-tech/pcsf
   cd pcsf
   pip install -e ".[dev]"
   pre-commit install

Tests and lint
--------------

.. code-block:: bash

   pytest                         # the whole suite
   pytest tests/studio            # PCSF Studio (needs the studio extra)
   ruff check src tests installers
   ruff format src tests

The Studio tests draw offscreen; set ``QT_QPA_PLATFORM=offscreen``
on a machine without a display.

Every change comes with tests under ``tests/``, which mirrors the
layout of the package. Exact round trips are tested with
:func:`numpy.array_equal`, not with tolerances.

Documentation
-------------

The pages are reStructuredText under ``docs/``; the API reference
is generated from the docstrings, which follow the numpydoc
convention.

.. code-block:: bash

   pip install -e ".[docs]"
   sphinx-build -b html docs docs/_build/html
   sphinx-build -b doctest docs docs/_build/doctest

The second command runs the examples of the pages. Read the Docs
builds the same sources from ``.readthedocs.yaml``.

Changing the specification
--------------------------

Open an issue labelled ``spec`` before a pull request, and update
``spec/``, the conformance suite and both encodings together.
