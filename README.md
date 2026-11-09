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
pip install "pcsf[studio]"          # + PCSF Studio (graphical application, planned)
pip install "pcsf[all]"             # everything
```

## Quick start

```python
import pcsf

model = pcsf.read("model.pcsf")            # .pcsf, .pcsm or .pcsm.gz, detected from content
print(pcsf.info(model))
pcsf.validate(model).raise_if_failed()     # conformance rules C1-C9
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
algorithms) and 2 (solver parsers and adapters, conformance suite,
JSON Schemas) are complete; PCSF Studio and the installers follow.
See [CHANGELOG.md](CHANGELOG.md).

## Citing

See [CITATION.cff](CITATION.cff). The format and its algorithms are
described in a manuscript in preparation for *Geophysics*.

## Licence

BSD 3-Clause. See [LICENSE](LICENSE).
