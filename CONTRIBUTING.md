# Contributing to pcsf

Thank you for helping. This guide covers the development set-up, the
code rules, and the three most common contributions: a new encoding, a
new solver adapter, and a new companion format.

## Set-up

```bash
git clone https://github.com/earthai-tech/pcsf
cd pcsf
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
pytest
```

## Code rules

- **Public versus internal.** Only `pcsf.api` (re-exported by `pcsf`) is
  public and versioned. Changing it needs a deprecation period
  (`@deprecated` in `pcsf.decorators`) and a CHANGELOG entry.
- **Base classes.** New data classes derive from
  `pcsf.api.property.PCSFObject` and use `@dataclass(repr=False)`;
  implement `validate()`.
- **Errors.** Raise subclasses of `pcsf.exceptions.PCSFError`, never bare
  `ValueError` or `RuntimeError`.
- **Dependencies.** The core needs NumPy and h5py only. Anything else is
  optional: import it through `pcsf.compat.optional.import_optional` or
  the `@requires` decorator, and add it to an extra in `pyproject.toml`.
- **Version differences** (Python, NumPy, h5py) go in `pcsf.compat`, nowhere else.
- **Helpers.** A helper used by one module stays in it; it moves to
  `pcsf.utils` when a second module needs it.
- **Style.** `ruff` (line length 99), NumPy-style docstrings, type hints
  on public functions. Equations in docstrings use the notation of the
  specification.
- **Tests.** Every change comes with tests under `tests/`, mirroring the
  package layout. Bit-exactness is tested with `np.array_equal`, not tolerances.

## Recipe 1: add an encoding

```python
# my_package/pcsf_plugin.py
import numpy as np
from pcsf.api.registry import register_encoding

def register_encodings():
    @register_encoding("log10_conductance", inverse=lambda rho: -np.log10(rho),
                       quantity="conductivity", description="log10 of S")
    def _to_rho(values):
        return 10.0 ** (-values)
```

```toml
# my_package/pyproject.toml
[project.entry-points."pcsf.encodings"]
my_encodings = "my_package.pcsf_plugin:register_encodings"
```

Files then declare `encoding="log10_conductance"`, and every reader with
the plugin installed converts them.

## Recipe 2: add a solver adapter

Write a parser in `pcsf/native/<solver>.py` (NumPy only, returns plain
arrays), then an adapter in `pcsf/adapters/<solver>.py` that builds a
`PCSFModel`, attaches the inversion record, and registers itself with
`@register_adapter("<solver>")`. Add a small real example to
`conformance/files/` and its expected values.

## Recipe 3: add a companion format

Boreholes, geology legends and other companion formats are separate
packages that register through the `pcsf.formats` entry-point group
(see `pcsf.plugins`).

## Changing the specification

The file format has its own version (`pcsf._version.FORMAT_VERSION`).
Additive, backward-compatible changes (a new optional field, kind or
encoding) are minor versions; anything else is a major version. Open an
issue labelled `spec` before a pull request, and update `spec/`, the
conformance suite and both encodings together.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
