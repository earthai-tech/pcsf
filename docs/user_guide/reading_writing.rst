Reading and writing
===================

One model, two encodings
------------------------

.. list-table::
   :header-rows: 1
   :widths: 16 20 64

   * - Encoding
     - Suffix
     - Description
   * - PCSF
     - ``.pcsf``
     - HDF5: binary, compressed, fast for large models
   * - PCSM
     - ``.pcsm``, ``.pcsm.gz``
     - plain text with comments, readable without any library;
       optionally gzip-compressed

The two hold the same information and convert into each other
without loss: the arrays that come back are equal bit for bit.

The facade
----------

Four functions cover the usual work. They accept ``str`` or
:class:`pathlib.Path`.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Function
     - Does
   * - :func:`pcsf.read`
     - read a ``.pcsf``, ``.pcsm`` or ``.pcsm.gz`` file; the
       encoding is detected from the content, not the suffix
   * - :func:`pcsf.write`
     - write a model; the encoding comes from the suffix
   * - :func:`pcsf.convert`
     - read one file and write another
   * - :func:`pcsf.detect`
     - name the encoding of a file

.. doctest::

   >>> from pcsf.adapters import occam2d_to_pcsf
   >>> model = occam2d_to_pcsf(pcsf.datasets.path("occam2d_tiny"))
   >>> binary = pcsf.write(model, "section.pcsf")
   >>> text = pcsf.convert(binary, "section.pcsm")
   >>> pcsf.detect(text)
   'pcsm'
   >>> again = pcsf.read(text)
   >>> bool(np.array_equal(again.resistivity, model.resistivity,
   ...                     equal_nan=True))
   True
   >>> bool(np.array_equal(again.resistivity_native,
   ...                     model.resistivity_native,
   ...                     equal_nan=True))
   True

Cells without a value are NaN in both encodings, hence
``equal_nan``.

A PCSM file reads as text. After its comment lines (``#``) come
the version and the keywords:

.. doctest::

   >>> lines = text.read_text().splitlines()
   >>> [ln for ln in lines if not ln.startswith("#")][:2]
   ['PCSM_VERSION 0.1.0', 'SOURCE_BACKEND occam2d']

Format-specific functions
-------------------------

The functions behind the facade are available when the encoding
is known in advance: :func:`pcsf.read_pcsf`,
:func:`pcsf.write_pcsf`, :func:`pcsf.read_pcsm`,
:func:`pcsf.write_pcsm`, and the file-to-file converters
:func:`pcsf.pcsf_to_pcsm` and :func:`pcsf.pcsm_to_pcsf`.

Versions
--------

Each file carries the version of the format it was written with
(|format_version| for this release), which is independent of the
package version. A reader accepts files of the same major version
and raises :class:`~pcsf.VersionError` for an unknown major
version.

Errors
------

Every error raised by the package derives from
:class:`~pcsf.PCSFError`:

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Exception
     - Raised when
   * - :class:`~pcsf.FormatError`
     - a file is not PCSF or PCSM, or is malformed
   * - :class:`~pcsf.PCSMSyntaxError`
     - a PCSM file breaks the grammar; the message gives the line
   * - :class:`~pcsf.VersionError`
     - the format version is not supported
   * - :class:`~pcsf.EncodingError`
     - a resistivity encoding is unknown
   * - :class:`~pcsf.GeometryError`
     - a geometry is inconsistent
   * - :class:`~pcsf.ConformanceError`
     - :meth:`~pcsf.core.conformance.ConformanceReport.raise_if_failed`
       finds a failed rule
   * - :class:`~pcsf.MissingDependencyError`
     - an optional package is needed and not installed
