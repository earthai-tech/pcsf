API reference
=============

The names of the first two sections, re-exported by :mod:`pcsf`,
are the stable public API and follow semantic versioning. The
other modules are documented for reference and may change between
minor versions.

.. currentmodule:: pcsf

Facade
------

.. autosummary::
   :toctree: generated
   :nosignatures:

   read
   write
   convert
   detect
   validate
   info

Data model
----------

.. autosummary::
   :toctree: generated
   :nosignatures:

   PCSFModel
   Grid2DGeometry
   Grid3DGeometry
   UnstructuredMeshGeometry
   MultilineGeometry
   LineEntry
   DerivedVolume
   StationTable
   TopographyPerStation
   TopographyRaster

Inversion record and provenance
-------------------------------

.. autosummary::
   :toctree: generated
   :nosignatures:

   InversionRecord
   attach_inversion_record
   get_inversion_record
   check_inversion_record
   ModelProvenance

Conformance
-----------

.. autosummary::
   :toctree: generated
   :nosignatures:

   check_conformance
   core.conformance.ConformanceReport
   core.conformance.RuleResult

Format-specific input and output
--------------------------------

.. autosummary::
   :toctree: generated
   :nosignatures:

   read_pcsf
   write_pcsf
   read_pcsm
   write_pcsm
   pcsf_to_pcsm
   pcsm_to_pcsf

Encodings
---------

.. autosummary::
   :toctree: generated
   :nosignatures:

   core.encodings.to_resistivity
   core.encodings.from_resistivity
   core.encodings.known_encodings
   core.encodings.is_known_encoding

Registries
----------

.. autosummary::
   :toctree: generated
   :nosignatures:

   api.registry.register_encoding
   api.registry.register_adapter
   api.registry.register_format
   api.registry.get_encoding
   api.registry.EncodingSpec
   api.registry.Registry
   plugins.load_plugins

Algorithms
----------

.. currentmodule:: pcsf.algorithms

.. autosummary::
   :toctree: generated
   :nosignatures:

   sample_log10
   interpolation_weights
   InterpolationWeights
   interpolated_std
   locate_triangles
   TriangleLocator
   compare_log10
   ComparisonResult
   log_uncertainty
   encoding_jacobian
   transform_covariance
   lognormal_relative_std
   node_to_cell
   mesh_to_grid2d
   register_frame
   decompose_frame
   FrameRegistration

Adapters
--------

.. currentmodule:: pcsf.adapters

.. autosummary::
   :toctree: generated
   :nosignatures:

   occam2d_to_pcsf
   modem_to_pcsf
   mare2dem_to_pcsf
   emc_to_pcsf
   pcsf_to_emc

Exceptions
----------

.. currentmodule:: pcsf.exceptions

.. autosummary::
   :toctree: generated
   :nosignatures:

   PCSFError
   FormatError
   PCSMSyntaxError
   VersionError
   EncodingError
   GeometryError
   ConformanceError
   AdapterError
   RegistryError
   MissingDependencyError

Decorators and datasets
-----------------------

.. currentmodule:: pcsf

.. autosummary::
   :toctree: generated
   :nosignatures:

   decorators.requires
   decorators.deprecated
   decorators.validates_model
   decorators.log_call
   datasets.path

PCSF Studio
-----------

.. currentmodule:: pcsf.studio

.. autosummary::
   :toctree: generated
   :nosignatures:

   main
   self_test
   sources.open_source
   sources.LoadedModel
   figures.views
   figures.draw
   figures.restyle
   figures.color_range
   figures.n_positions
   figures.position_label
   figures.view_values
   summary.value_stats
   summary.summary_rows
   summary.station_rows
   summary.record_rows
   summary.conformance_rows
   summary.metadata_tree
   summary.cell_table
   summary.write_csv
   style.Theme
   style.get_theme
   style.style_sheet
   window.ModelView
   window.StudioWindow
