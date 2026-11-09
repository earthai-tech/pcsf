# Changelog

All notable changes are documented here. The package follows
[semantic versioning](https://semver.org); the file format has its own
version (`FORMAT_VERSION`), documented in `spec/`.

## [Unreleased] — 0.1.0.dev0

First release as a standalone package, extracted from pyCSAMT's
`pycsamt.format` subpackage.

### Added
- `pcsf.api`: stable facade (`read`, `write`, `convert`, `detect`, `validate`,
  `info`), base classes `PCSFObject` and `MetadataMixin`, public types, and
  registries for encodings, adapters and companion formats.
- `pcsf.exceptions`: error hierarchy rooted at `PCSFError`.
- `pcsf.decorators`: `requires`, `deprecated`, `validates_model`, `log_call`.
- `pcsf.compat`, `pcsf.utils`: version shims, optional imports, helpers.
- `pcsf.core.encodings`: encoding registry; built-in `log10`, `ln`, `linear`,
  `log10_conductivity`, `conductivity`.
- `pcsf.core.conformance`: rules C1–C9 and `ConformanceReport`.
- `pcsf.algorithms`: NumPy-only multilinear sampling with exposed weights,
  triangle point location, comparison statistics, uncertainty propagation
  (encodings, full covariance, resampling variance), node-to-cell
  projection, frame registration and decomposition, mesh-to-grid export.
- `pcsf.plugins`: entry-point discovery for `pcsf.encodings`,
  `pcsf.adapters`, `pcsf.formats`.
- `pcsf` command-line tool: `info`, `validate`, `convert`, `compare`, `version`.

### Changed (relative to pycsamt.format)
- The acronym now stands for *Portable* Common Subsurface Format.
- Sampling and point location no longer need SciPy or Matplotlib; results
  agree with the previous implementation to 1e-10.
- Errors are `PCSFError` subclasses (still `ValueError` subclasses where
  they were `ValueError` before).
- The optional borehole group is carried through unchanged; its meaning
  belongs to the borehole companion format.
