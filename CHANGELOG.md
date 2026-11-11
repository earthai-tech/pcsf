# Changelog

All notable changes are documented here. The package follows
[semantic versioning](https://semver.org); the file format has its own
version (`FORMAT_VERSION`), documented in `spec/`.

## [Unreleased]

## [0.1.0] — 2026-11-11

First release of pcsf as a standalone package: the reference
implementation of the Portable Common Subsurface Format (format
version 0.1.0), extracted from pyCSAMT's `pycsamt.format` subpackage.

### Highlights
- One file format for electromagnetic and magnetotelluric inversion
  models, in two encodings that convert into each other bit for bit:
  **PCSF** (HDF5) and **PCSM** (plain text, optionally `.pcsm.gz`).
- Readers of Occam2D, ModEM, MARE2DEM and EarthScope EMC output that
  need no inversion package.
- **PCSF Studio**, a desktop application to view, inspect and convert
  models, with installers for Windows and Linux that need no Python.
- Documentation at https://pcsf.readthedocs.io.

### Format and core
- Data model of the specification `spec/pcsf-0.1.md`: canonical
  resistivity in linear ohm m with the source values and their
  encoding kept unchanged; four geometry kinds (`grid2d`, `grid3d`,
  `mesh_unstructured`, `multiline`), never resampled; station table,
  topography and coordinate reference system; inversion record (data,
  errors, solver, regularization, misfit, convergence, depth of
  investigation) with a completeness check.
- `pcsf.read`, `write`, `convert`, `detect`, `validate`, `info`: the
  stable public API (`pcsf.api`), with base classes, public types and
  registries for encodings, adapters and companion formats.
- Encodings `log10`, `ln`, `linear`, `log10_conductivity` and
  `conductivity`, and a registry for more.
- Conformance rules C1–C10 (`pcsf.validate`, `ConformanceReport`).
  Mesh region ids are 0-based indices into the per-region table
  (rule C10).
- JSON Schemas of the inversion record and of the provenance of
  models from learned predictors (`pcsf[schema]` to validate).
- Conformance suite for independent implementations: 27 reference
  files (15 valid, 8 rule-breaking, 4 to reject), `expected.json` and
  the runner `conformance/run.py`.
- Error hierarchy rooted at `PCSFError` (`pcsf.exceptions`); the
  decorators `requires`, `deprecated`, `validates_model`, `log_call`.

### Solver output
- NumPy-only parsers (`pcsf.native`) of Occam2D (mesh, model,
  iteration, data, log), ModEM (`.rho`, `.dat`, NLCG log) and
  MARE2DEM (`.resistivity`, `.poly`, log) files.
- Adapters `occam2d_to_pcsf` (run folder), `modem_to_pcsf`,
  `mare2dem_to_pcsf`, and `emc_to_pcsf` / `pcsf_to_emc` for the
  netCDF archives of the EarthScope Earth Model Collaboration. On the
  field runs of the paper they reproduce pyCSAMT's arrays bit for
  bit, and the EMC round trips are lossless.
- Other solvers, encodings and companion formats plug in through the
  entry points `pcsf.adapters`, `pcsf.encodings` and `pcsf.formats`.
- `pcsf.datasets`: tiny Occam2D, ModEM and MARE2DEM runs for examples
  and tests.

### Algorithms
- `pcsf.algorithms`, NumPy only: multilinear sampling with its
  weights exposed, point location in triangle meshes, comparison
  statistics, propagation of uncertainty (between encodings, full
  covariance, resampling variance), node-to-cell projection, frame
  registration and decomposition, mesh-to-grid export.

### Tools
- Command line `pcsf`: `info`, `validate`, `convert`, `compare`,
  `studio`, `version`.
- PCSF Studio (`pcsf[studio]`, `pcsf-studio`):
  - opens `.pcsf`, `.pcsm`, `.pcsm.gz`, Occam2D, ModEM and MARE2DEM
    runs and EMC files, from the toolbar or by drag and drop;
  - sections, depth slices, x/y sections, meshes and lines, with
    stations and topography, a colour range that ignores air cells, a
    depth limit and a fit to the survey;
  - an inspector (summary, stations, metadata, inversion record,
    conformance, reading notes) and a statistics panel that collapses
    to the right;
  - a Convert page that turns many solver runs into `.pcsf`, `.pcsm`
    or `.pcsm.gz` in one go, in the background, with a log;
  - exports of figures (PNG, SVG, PDF) and of cells and stations
    (CSV); light, dark and system themes; `--self-test`;
  - `ModelView` and `ConvertPage` can be embedded in other Qt
    applications (pyCSAMT's desktop application embeds the viewer).
- Installers that need no Python: Windows `setup.exe` (optional
  desktop icon and `.pcsf`/`.pcsm` association), Linux AppImage and a
  self-extracting `.sh` (`installers/`, built and attached to each
  release by `studio-installers.yml`).

### Documentation and reproducibility
- Documentation on Read the Docs with a version switcher: getting
  started, user guide, a PCSF Studio guide with screenshots, API
  reference, specification and development guide.
- `paper/`: reproduction of every number, table and figure of the
  paper that describes the format (`run_all.py`, `--rebuild`,
  `check_results.py`, data archive fetched by `fetch_data.py`).
- Workflows: tests on Linux, macOS and Windows with Python 3.9, 3.11 and 3.13,
  coverage (Codecov), documentation build, Studio installers, and
  publication on TestPyPI then PyPI from version tags on master.

### Changed relative to `pycsamt.format`
- The acronym now stands for *Portable* Common Subsurface Format.
- Sampling and point location no longer need SciPy or Matplotlib;
  results agree with the previous implementation to 1e-10.
- Errors are `PCSFError` subclasses (still `ValueError` subclasses
  where they were `ValueError` before).
- Mesh region ids are 0-based: the MARE2DEM adapters of pcsf and
  pyCSAMT stored MARE2DEM's own numbering, which starts at 1; they now
  convert it once, on conversion. The per-triangle resistivity was
  correct in every file.
- The PCSM reader raises `GeometryError` instead of a bare NumPy
  `ValueError` when a block holds the wrong number of values.
- The optional borehole group is read as the dictionary it stores
  unless a companion format registered for it decodes it.

[Unreleased]: https://github.com/earthai-tech/pcsf/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/earthai-tech/pcsf/releases/tag/v0.1.0
