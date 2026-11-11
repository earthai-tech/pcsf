Command line
============

Installing the package adds the ``pcsf`` command. Each subcommand
has its own help, ``pcsf <command> --help``.

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Does
   * - ``pcsf info FILE``
     - describe a PCSF or PCSM file
   * - ``pcsf validate FILE [FILE ...]``
     - check the conformance rules on each file
   * - ``pcsf convert SRC DST``
     - convert between ``.pcsf``, ``.pcsm`` and ``.pcsm.gz``; the
       target encoding comes from the suffix of ``DST``
   * - ``pcsf compare A B``
     - compare two models defined on the same grid
   * - ``pcsf studio``
     - open PCSF Studio (needs the ``studio`` extra)
   * - ``pcsf version``
     - print the package and format versions

Examples
--------

.. code-block:: bash

   pcsf info model.pcsf
   pcsf validate *.pcsf
   pcsf convert model.pcsf model.pcsm
   pcsf convert --log10-view model.pcsf model.pcsm
   pcsf compare a.pcsf b.pcsf

``--log10-view`` adds a :math:`\log_{10}\rho` view to a PCSM
output, for reading by eye; the canonical values stay linear.

PCSF Studio has its own launcher, described in
:doc:`../studio/index`:

.. code-block:: bash

   pcsf-studio model.pcsf
   pcsf-studio --theme dark
   pcsf-studio --self-test
