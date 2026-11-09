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

### Added in phase 2
- `pcsf.native`: NumPy-only parsers of Occam2D (mesh, model, iteration,
  data, log), ModEM (`.rho`, `.dat`, NLCG log) and MARE2DEM
  (`.resistivity`, `.poly`, log) files.
- `pcsf.adapters`: `occam2d_to_pcsf` (run folder), `modem_to_pcsf`,
  `mare2dem_to_pcsf` and `emc_to_pcsf` / `pcsf_to_emc`, registered in
  `ADAPTERS`. On the paper's field runs and on the bundled runs they
  reproduce pyCSAMT's arrays bit for bit; EMC round trips are lossless.
- `pcsf.datasets`: tiny synthetic Occam2D, ModEM and MARE2DEM runs.
- `conformance/`: 25 reference files (valid, rule-breaking, rejected),
  `expected.json` and the runner `run.py`.
- `pcsf.schemas`: JSON Schemas of the inversion record and the model
  provenance; extra `pcsf[schema]` for validation.

### Fixed
- The PCSM reader raised a bare NumPy `ValueError` when a block held
  the wrong number of values; it now raises `GeometryError`.
- PCSM comments referred to `SPEC.md`; they now cite
  `spec/pcsf-0.1.md`.

### Changed (relative to pycsamt.format)
- The acronym now stands for *Portable* Common Subsurface Format.
- Sampling and point location no longer need SciPy or Matplotlib; results
  agree with the previous implementation to 1e-10.
- Errors are `PCSFError` subclasses (still `ValueError` subclasses where
  they were `ValueError` before).
- The optional borehole group is carried through unchanged; its meaning
  belongs to the borehole companion format.
