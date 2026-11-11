<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/earthai-tech/pcsf/master/docs/_static/logo/pcsf-logo-dark.svg">
    <img src="https://raw.githubusercontent.com/earthai-tech/pcsf/master/docs/_static/logo/pcsf-logo.svg" alt="PCSF: Portable Common Subsurface Format" width="560">
  </picture>
  <br/><br/>
  <a href="https://pypi.org/project/pcsf/"><img alt="PyPI" src="https://img.shields.io/pypi/v/pcsf?color=orange&label=PyPI"/></a>
  <a href="https://github.com/earthai-tech/pcsf/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/earthai-tech/pcsf?label=release&color=blueviolet"/></a>
  <a href="https://github.com/earthai-tech/pcsf/actions/workflows/ci.yml?query=branch%3Amaster"><img alt="CI" src="https://github.com/earthai-tech/pcsf/actions/workflows/ci.yml/badge.svg?branch=master"/></a>
  <a href="https://github.com/earthai-tech/pcsf/actions/workflows/docs.yml?query=branch%3Amaster"><img alt="Docs" src="https://github.com/earthai-tech/pcsf/actions/workflows/docs.yml/badge.svg?branch=master"/></a>
  <a href="https://codecov.io/gh/earthai-tech/pcsf"><img alt="Coverage" src="https://codecov.io/gh/earthai-tech/pcsf/branch/master/graph/badge.svg"/></a>
  <a href="https://opensource.org/licenses/BSD-3-Clause"><img alt="License" src="https://img.shields.io/badge/license-BSD--3--Clause-blue"/></a>
  <br/>
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white"/>
  <img alt="Format" src="https://img.shields.io/badge/PCSF%20format-0.1.0-2f5fd0"/>
  <img alt="Platform" src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey"/>
  <a href="https://github.com/astral-sh/ruff"><img alt="Code style: ruff" src="https://img.shields.io/badge/code%20style-ruff-D7FF64?logo=ruff&logoColor=black"/></a>
  <br/>
  <a href="https://pypi.org/project/pcsf/"><img alt="Downloads" src="https://img.shields.io/pypi/dm/pcsf?label=downloads&color=brightgreen"/></a>
  <a href="https://github.com/earthai-tech/pcsf/commits/master"><img alt="Last commit" src="https://img.shields.io/github/last-commit/earthai-tech/pcsf/master"/></a>
  <a href="https://github.com/earthai-tech/pcsf/issues"><img alt="Issues" src="https://img.shields.io/github/issues/earthai-tech/pcsf"/></a>
  <a href="https://github.com/earthai-tech/pcsf/pulls"><img alt="PRs welcome" src="https://img.shields.io/badge/PRs-welcome-brightgreen"/></a>
  <a href="https://github.com/earthai-tech/pcsf/blob/master/CODE_OF_CONDUCT.md"><img alt="Contributor Covenant" src="https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg"/></a>
  <br/><br/>
  <strong><a href="https://earthai-tech.github.io/pcsf/">Documentation</a></strong> &middot;
  <a href="https://github.com/earthai-tech/pcsf/tree/master/spec">Specification</a> &middot;
  <a href="#pcsf-studio">PCSF Studio</a> &middot;
  <a href="https://github.com/earthai-tech/pcsf/blob/master/CHANGELOG.md">Changelog</a>
</div>

---

# pcsf — Portable Common Subsurface Format

**pcsf** is an exchange format for electromagnetic and magnetotelluric
inversion models, with the tools and algorithms to read, write, validate,
sample and compare them.

Every inversion code writes its own format, with its own logarithm base,
axis order, coordinate frame, depth datum and discretization. A reader
who does not know these conventions misreads the model, and the errors
are of the same size as the geological contrasts the model is meant to
show. PCSF states them in the file:

- **canonical resistivity** in linear ohm m, with the source values and
  their encoding kept unchanged (`log10`, `ln`, `linear`, `log10_conductivity`,
  `conductivity`, or a plugin encoding);
- **native geometry**: 2D section (`grid2d`), 3D grid (`grid3d`), triangular
  mesh (`mesh_unstructured`) or set of profiles (`multiline`), never resampled;
- **spatial reference**: station table, topography, coordinate reference system;
- **inversion record**: data, errors, solver, regularization, misfit,
  convergence and depth of investigation, with a completeness check.

One model, two encodings that convert into each other without loss:
**PCSF** (HDF5, binary, compressed) and **PCSM** (plain text, comments
allowed, optionally `.pcsm.gz`).

## Install

```bash
pip install pcsf                    # core: NumPy + h5py only
pip install "pcsf[emc]"             # + EarthScope/IRIS EMC netCDF archives
pip install "pcsf[mare2dem]"        # + triangulation of MARE2DEM models
pip install "pcsf[studio]"          # + PCSF Studio (graphical viewer)
pip install "pcsf[all]"             # everything
```

## Quick start

```python
import pcsf

model = pcsf.read("model.pcsf")            # .pcsf, .pcsm or .pcsm.gz, detected from content
print(pcsf.info(model))
pcsf.validate(model).raise_if_failed()     # conformance rules C1-C10
pcsf.write(model, "model.pcsm.gz")         # lossless text copy

from pcsf.algorithms import sample_log10, compare_log10

# solver output, without any inversion package
from pcsf.adapters import occam2d_to_pcsf, modem_to_pcsf
model = occam2d_to_pcsf("occam_run/")      # folder of an Occam2D run
model = modem_to_pcsf("run/m_NLCG_100.rho", data="run/d.dat")
```

Command line:

```bash
pcsf info model.pcsf
pcsf validate *.pcsf
pcsf convert model.pcsf model.pcsm
pcsf compare a.pcsf b.pcsf
```

## Repository layout

| Path | Content |
|---|---|
| `spec/` | versioned specification and PCSM grammar (EBNF); JSON Schemas in `src/pcsf/schemas/` |
| `conformance/` | reference files and expected values for independent implementations |
| `src/pcsf/api/` | **stable public API**: facade, base classes (`property.py`), types, registry |
| `src/pcsf/core/` | data model, encodings, versioning, HDF5 and text I/O, records, conformance |
| `src/pcsf/algorithms/` | sampling, point location, comparison, uncertainty, projection, registration |
| `src/pcsf/native/`, `adapters/` | solver parsers and converters (Occam2D, ModEM, MARE2DEM, EMC) |
| `src/pcsf/plugins/` | entry-point discovery (`pcsf.encodings`, `pcsf.adapters`, `pcsf.formats`) |
| `src/pcsf/cli/`, `studio/` | command-line tool, graphical application |
| `src/pcsf/utils/`, `compat/` | shared helpers, version and optional-dependency shims |
| `src/pcsf/decorators.py`, `exceptions.py` | shared decorators, error hierarchy |
| `installers/` | Windows `.exe`, Linux `.AppImage` / `.sh` builds |
| `paper/` | reproduction of the Geophysics paper |

Everything under `pcsf.api` (and re-exported by `pcsf`) follows semantic
versioning; other modules are internal.

## Status

Version 0.1.0.dev0, format version 0.1.0. Phases 1 (core and
algorithms), 2 (solver parsers and adapters, conformance suite, JSON
Schemas), 4 (PCSF Studio and its installers) and 5 (reproduction of
the paper, [paper/](paper/README.md)) are complete; pyCSAMT uses pcsf
as its format core (phase 3). See
[CHANGELOG.md](CHANGELOG.md).

## PCSF Studio

PCSF Studio is a viewer and inspector: it opens `.pcsf` and `.pcsm`
files, Occam2D, ModEM and MARE2DEM runs and EMC netCDF files; draws
sections, depth slices, meshes and lines; lists stations, metadata,
the inversion record and the conformance rules; converts solver runs
(Occam2D folders, ModEM, MARE2DEM and EMC files) to `.pcsf`, `.pcsm`
or `.pcsm.gz` in batches on its Convert page; and exports figures and
CSV tables. The statistics panel collapses to the right to give the
plot more room.

```bash
pip install "pcsf[studio]"
pcsf-studio model.pcsf           # or: pcsf studio, python -m pcsf.studio
pcsf-studio --self-test          # check an installation
```

Installers that need no Python (Windows `setup.exe`, Linux AppImage
and self-extracting `.sh`) are built by
[installers/build.py](installers/README.md) and attached to each
release. Its widget `pcsf.studio.ModelView` can be embedded in other
Qt applications.

## Citing

See [CITATION.cff](CITATION.cff). The format and its algorithms are
described in a manuscript in preparation for *Geophysics*.

## Licence

BSD 3-Clause. See [LICENSE](LICENSE).
