# Reproduction of the Geophysics paper

Scripts that regenerate every number, table and figure of the paper
*PCSF: a geometry-aware exchange format for electromagnetic inversion
models* (manuscript in preparation for *Geophysics*).

## Two tiers

| Tier | Command | Needs | Time |
|---|---|---|---|
| 1 | `python paper/run_all.py` | pcsf, the data archive | minutes |
| 2 | `python paper/run_all.py --rebuild` | tier 1 + pyCSAMT | minutes |

**Tier 1** reads the archived models (`data/models`, `.pcsf` and
`.pcsm`) and the native solver files they came from (`data/native`),
and runs every analysis of the paper: source fidelity (test 1),
sampling accuracy (test 2), independent readers (test 3), storage
(test 4), the ambiguities of native files, the 2D/3D field comparison,
frame registration and uncertainty, the EMC round trips, and all
figures. It uses pcsf and no pyCSAMT.

**Tier 2** first rebuilds the models from the native runs and the
processed EDI files (station coordinates and elevations, inversion
records, depth of investigation, multi-line assembly), which uses
pyCSAMT, writes them to `output/models` and then runs tier 1 on them.

## Steps

```bash
pip install -e ".[algorithms,emc,mare2dem,geo]" -r paper/requirements.txt
python paper/fetch_data.py                    # data archive -> paper/data
python paper/run_all.py                       # -> paper/output
python paper/check_results.py                 # compare with expected/
```

For tier 2, add `pip install -r paper/requirements-rebuild.txt` and
run `python paper/run_all.py --rebuild`.

Test 3 also needs `h5dump`, the HDF5 command-line tool, on `PATH`
(`conda install -c conda-forge hdf5` in a separate environment, or
`apt install hdf5-tools`). Test 4 times reading and writing; its
timings depend on the computer, so `check_results.py` compares its
file sizes but not its times.

## Data

The archive `pcsf-paper-data-<version>.zip` (Zenodo, see
`data_source.json`) unpacks into `paper/data`:

| Folder | Contents | Source |
|---|---|---|
| `models/` | the 14 models of the paper, `.pcsf` and `.pcsm` | converted from the runs below |
| `native/occam2d/tongkeng/` | Occam2D run, Tongkeng CSAMT line | Kouadio et al. (2020) |
| `native/occam2d/baohuashan/L18PLT` ... `L34PLT` | Occam2D runs, five Baohuashan AMT lines (data files for L18 and L22 only) | Kouabena et al. (2025) |
| `native/modem/baohuashan/` | ModEM 3D inversion, Baohuashan survey (model and log; no data file) | Kouabena et al. (2025) |
| `native/modem/sample/` | ModEM 3D sample run (27 frequencies; no data file) | pyCSAMT sample data |
| `native/mare2dem/demo/` | MARE2DEM demonstration inversion | MARE2DEM distribution |
| `native/emc/` | three EMC netCDF files and the ModEM models they derive from, with their readme files | IRIS EMC (USGS models, Bedrosian et al.) |
| `edi/baohuashan/` | processed EDI files of lines L18 and L22 | Kouabena et al. (2025) |
| `tables/` | run summary of the Occam2D lines | |
| `rebuild/` | earlier conversions with station tables, synthetic predictions, Tongkeng topography | pyCSAMT examples |

Of each Occam2D run, the archive keeps the mesh, model, data, startup,
log, every iteration file and the final response; the console logs
(up to 240 MB per run) are left out.

Only lines L18 and L22 of the Baohuashan survey are public. The
archive holds the models of all lines, but the measured data of
lines L26, L30 and L34 (EDI files, Occam2D data files and responses)
and the data files of the two ModEM runs, which hold all stations,
are left out and listed in `data/RESTRICTED.txt`; they are available
from the authors on reasonable request. Tier 1 needs none of them.
Tier 2 rebuilds what the public data allow and takes the other
Baohuashan models, with their inversion records, from `data/models`. `data/SHA256SUMS` lists every
file; `fetch_data.py --check` re-checks them.

`tools/make_data_archive.py` assembles the archive from the authors'
working copies; reviewers do not need it.

## Layout

```
paper/
  run_all.py, fetch_data.py, check_results.py
  data_source.json      Zenodo record and archive checksum
  scripts/              one script per analysis; paths.py, figstyle.py
  expected/             the tables reported in the paper
  tools/                archive assembly (authors only)
  data/                 unpacked archive (not in git)
  output/               results/, figures/, models/ (not in git)
```

`PCSF_PAPER_DATA` and `PCSF_PAPER_OUT` move the data and output
folders (see `scripts/paths.py`).
