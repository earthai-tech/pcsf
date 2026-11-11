Reference
=========

Keyboard shortcuts
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Keys
     - Action
   * - :kbd:`Ctrl+O`
     - open a file
   * - :kbd:`Ctrl+Shift+O`
     - open a run folder
   * - :kbd:`Ctrl+Shift+C`
     - the Convert page
   * - :kbd:`F5`
     - read the model again from disk
   * - :kbd:`Ctrl+Shift+S`
     - save as PCSF, PCSM or PCSM gzip
   * - :kbd:`Ctrl+E`
     - export the figure
   * - :kbd:`Ctrl+Home`
     - start page
   * - :kbd:`Ctrl+1`
     - show or hide the inspector
   * - :kbd:`Ctrl+2`
     - collapse or expand the statistics
   * - :kbd:`Ctrl+T`
     - switch between the light and the dark theme
   * - :kbd:`F1`
     - list of shortcuts
   * - :kbd:`Ctrl+Q`
     - quit

Settings
--------

The application remembers its theme, the layout of its panels, the
recent files, and the formats and folder of the Convert page. It
always opens at its default size, centred on the screen; *View >
Reset window size* brings it back to that size during a session.
The settings are kept per user: in the registry on Windows
(``HKEY_CURRENT_USER\Software\earthai-tech\PCSF Studio``) and in
``~/.config/earthai-tech/PCSF Studio.conf`` on Linux.

Without a window
----------------

The parts that open, draw and convert models need no Qt and can be
used in scripts:

.. doctest::

   >>> import matplotlib
   >>> matplotlib.use("Agg")
   >>> from matplotlib.figure import Figure
   >>> from pcsf.studio.sources import open_source
   >>> from pcsf.studio import figures
   >>> loaded = open_source(pcsf.datasets.path("modem_tiny"))
   >>> loaded.kind, loaded.model.kind
   ('modem', 'grid3d')
   >>> figures.views(loaded.model)
   ('depth slice', 'x section', 'y section')
   >>> ax = figures.draw(Figure(), loaded.model, "x section", index=2)
   >>> ax.get_xlabel(), ax.get_ylabel()
   ('y (m)', 'depth (m)')

Embedding the viewer
--------------------

:class:`~pcsf.studio.window.ModelView`, the widget that shows one
model with its inspector, plot and statistics, can be placed in
another Qt application; pyCSAMT's desktop application does so.

.. code-block:: python

   from pcsf.studio import ModelView
   from pcsf.studio.sources import open_source
   from pcsf.studio.style import DARK, style_sheet

   view = ModelView()
   view.setStyleSheet(style_sheet(DARK))
   view.set_theme(DARK)
   view.set_model(open_source("model.pcsf"))
   layout.addWidget(view)

:class:`~pcsf.studio.convert_page.ConvertPage` can be embedded the
same way.

Questions
---------

.. dropdown:: Does PCSF Studio change my files?

   No. It reads files and run folders and writes only what you ask
   for: *Save as*, the exports, and the outputs of the Convert page,
   which by default never replace an existing file.

.. dropdown:: Why are the top cells of my model blank?

   Cells above :math:`10^{8}\ \Omega\,`\ m are air and are not
   drawn, so the topography is the upper edge of the model. The
   statistics count them under *Air / missing*.

.. dropdown:: A ModEM model has a note about the station Z column

   ModEM data files give station heights either as elevations or as
   depths, and do not say which. When the values look like depths,
   the adapter converts them and writes a note, shown in the
   *Reading* tab and in the Convert log. Convert the model in Python
   with ``station_z_convention="elevation"`` to keep the values as
   they are.

.. dropdown:: Where do I report a problem?

   On the `issue tracker
   <https://github.com/earthai-tech/pcsf/issues>`__, with the output
   of ``pcsf-studio --self-test --report report.txt``.
