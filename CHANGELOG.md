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
- `conformance/`: 27 reference files (valid, rule-breaking, rejected),
  `expected.json` and the runner `run.py`.
- `pcsf.schemas`: JSON Schemas of the inversion record and the model
  provenance; extra `pcsf[schema]` for validation.

### Added in phase 4
- `pcsf.studio`, PCSF Studio: a PySide6 viewer and inspector of
  `.pcsf`/`.pcsm` files, native runs (Occam2D, ModEM, MARE2DEM) and
  EMC netCDF files. Sections, depth slices, x/y sections, meshes and
  multi-line views in matplotlib, with an automatic colour range that
  ignores air cells, a depth limit and a fit to the survey; tables of
  stations, metadata, inversion record and conformance; conversion
  between PCSF and PCSM; PNG/SVG/PDF and CSV exports. The parts
  without Qt (`sources`, `figures`, `summary`) are usable on their
  own, and `ModelView` embeds in other Qt applications.
- `pcsf-studio` launcher, `pcsf studio` command and
  `python -m pcsf.studio`; `--self-test` checks an installation
  without a window.
- `installers/`: PyInstaller spec, Inno Setup script (Windows
  `setup.exe`, optional `.pcsf`/`.pcsm` association), AppImage and
  makeself packaging (Linux), and `build.py`, which freezes the
  application, runs the frozen self-test and packages it. The
  workflow `studio-installers.yml` builds them on every tag.
- `read_pcsf` decodes the borehole group through a companion format
  registered under its kind (`register_format("pcbh", ...)` with a
  `from_dict`), and returns the stored dictionary otherwise.

### Added in phase 5
- `paper/`: reproduction of the Geophysics paper. Tier 1
  (`run_all.py`) reruns every analysis and figure with pcsf alone
  from the archived models and native runs; tier 2
  (`run_all.py --rebuild`) first rebuilds the models from the raw
  runs and EDI files with pyCSAMT. `check_results.py` compares the
  output with the tables of the paper (`expected/`); both tiers
  reproduce all of them. `fetch_data.py` downloads and checks the
  data archive (Zenodo, `data_source.json`);
  `tools/make_data_archive.py` assembles it.
- PCSF Studio, new layout: toolbar with the logo at the far left
  (it leads to the start page), samples and export menus, and the
  theme and `?` help menus at the far right; start page with recent
  files, header with status chips (geometry, solver, conformance,
  inversion record), and a statistics panel (whole model and current
  view: cells, air and missing cells, median, 5-95 % range, mean and
  spread of log10 rho, histogram with the colour range).
- PCSF Studio themes: light, dark, or the one of the desktop
  (`pcsf.studio.style.Theme`, `LIGHT`, `DARK`, `get_theme`,
  `style_sheet`; `StudioWindow.set_theme`, `ModelView.set_theme`,
  `pcsf-studio --theme`). Plots follow the theme on screen and are
  exported on a white background (`ModelView.save_figure`,
  `pcsf.studio.figures.restyle`).
- PCSF Studio window: opens centred, at most 82 % of the available
  screen; remembers its size, theme and panel layout; panels that
  do not fit scroll instead of being cut; inspector and statistics
  can be hidden (View menu); reload (F5).
- PCSF Studio error handling: a view that cannot be drawn is
  reported on the plot (`ModelView.plot_failed`), a failed open
  keeps the model shown before, error dialogs carry the traceback,
  and unexpected errors are reported instead of ending the program.
- `pcsf.studio.figures.view_values`, `pcsf.studio.summary.value_stats`.
- SVG logo (`studio/resources/pcsf-studio.svg`), from which
  `installers/make_icon.py` renders the PNG and ICO icons; the
  self-test checks that it renders.
- `installers/build.sh` and `installers/build.ps1`.

### Changed in phase 5
- Mesh region ids are 0-based indices into the per-region table
  (specification, `geometry/region_ids`). The MARE2DEM adapters of
  pcsf and pyCSAMT stored MARE2DEM's own numbering, which starts at 1,
  while the rest of the package and the conformance check assumed 0;
  they now convert it once, on conversion. `expand_regions` takes
  0-based ids. The per-triangle resistivity was correct in every file.
- New conformance rule C10 (`0 <= region id < n_regions`) and the
  rule-breaking case `rule_c10_region_base`.

### Fixed
- The CI workflow ran on pushes to `main`, a branch the repository
  does not have; it now runs on `master`.
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
- The optional borehole group is read as the dictionary it stores
  unless a companion format registered for it decodes it; its
  meaning belongs to the borehole companion format.
