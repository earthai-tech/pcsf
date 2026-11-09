# Conformance suite

Reference files and expected outcomes that any implementation of
PCSF (Python, MATLAB, Julia, C, ...) can use to show that it reads
the format correctly. The expectations in `expected.json` are plain
JSON, so a runner in another language needs no Python.

## Content

- `files/`: the reference files.
- `expected.json`: the outcome each file must produce.
- `run.py`: the reference runner (`python conformance/run.py`).

## Cases

**valid** (15 files): five models in `.pcsf`, `.pcsm` and
`.pcsm.gz`, converted from the tiny synthetic runs in
`pcsf.datasets`:

| Case | Kind | What it exercises |
|---|---|---|
| `grid2d_occam2d` | grid2d | air row (NaN), log10 source values, stations with lon/lat and topography |
| `grid3d_modem` | grid3d | ln source values, masked air fill, origin, depth-to-elevation stations |
| `mesh_mare2dem` | mesh_unstructured | per-region table, air region at 1e12 ohm m |
| `multiline` | multiline | two lines with real offsets and a synthesized volume |
| `grid2d_with_record` | grid2d | complete inversion record in metadata |

A reader must read each file, pass every conformance rule, and
reproduce the canonical resistivity bit for bit: the SHA-256 of the
array as little-endian float64 in C order must equal
`resistivity_sha256`.

**rule** (6 files): readable files that break exactly one rule, in
`.pcsf` and `.pcsm`. A reader must report that rule, and only it, as
failed.

| Case | Rule |
|---|---|
| `rule_c2_negative` | C2: negative resistivity |
| `rule_c5_native_mismatch` | C5: source values do not reproduce the canonical values |
| `rule_c7_not_synthesized` | C7: derived volume not labelled synthesized |

**reject** (4 files): PCSM text altered so that a reader must refuse
it. `error` names the pcsf exception; other implementations map it to
their own error of the same meaning.

| Case | Error | Alteration |
|---|---|---|
| `reject_unknown_encoding` | EncodingError | encoding `log7` |
| `reject_shape_mismatch` | GeometryError | 3 columns declared, 2 values given |
| `reject_major_version` | VersionError | `PCSM_VERSION 9.0.0` |
| `reject_missing_block_end` | PCSMSyntaxError | `END_RESISTIVITY` removed |

## Regenerating

The files are produced deterministically (fixed creation time) by

    python tools/make_conformance_suite.py

Only the gzip headers of `.pcsm.gz` files change between runs; their
content does not.
