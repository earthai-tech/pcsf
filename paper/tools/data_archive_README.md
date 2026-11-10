# Data archive of the PCSF paper

Data needed to reproduce every number, table and figure of

> Kouadio, K. L., *A geometry-aware exchange format for
> electromagnetic inversion models* (manuscript submitted to
> *Geophysics*).

The archive holds the inversion models of the paper in the Portable
Common Subsurface Format (PCSF, HDF5) and its text encoding (PCSM),
the native solver files they were converted from, the processed EDI
files that the rebuild of the models reads, and three models of the
EarthScope Earth Model Collaboration (EMC). The code that reads it is
the `paper/` folder of the pcsf repository:

    python paper/fetch_data.py --file pcsf-paper-data-1.zip
    python paper/run_all.py             # tier 1: all analyses
    python paper/run_all.py --rebuild   # tier 2: rebuild models first
    python paper/check_results.py       # compare with the paper

## Contents (`data/`)

| Folder | Contents | Source |
|---|---|---|
| `models/` | the 14 models of the paper, `.pcsf` and `.pcsm` | converted from the runs below |
| `native/occam2d/tongkeng/` | Occam2D run, Tongkeng CSAMT profile | Kouadio et al. (2020), doi:10.1016/j.jappgeo.2020.104204 |
| `native/occam2d/baohuashan/L18PLT` ... `L34PLT` | Occam2D runs of five Baohuashan AMT lines; data files and responses for L18 and L22 only | Kouabena et al. (2025), doi:10.1016/j.oregeorev.2025.106798 |
| `native/modem/baohuashan/` | ModEM 3D inversion of the Baohuashan survey: final model, log and control file | Baohuashan survey |
| `native/modem/sample/` | ModEM 3D sample run (27 frequencies): final model, log and control file | pyCSAMT sample data |
| `native/mare2dem/demo/` | MARE2DEM demonstration inversion | MARE2DEM distribution |
| `native/emc/` | three EMC netCDF files and the ModEM models they derive from, with their readme files | EarthScope EMC (see below) |
| `edi/baohuashan/L18PLT`, `L22PLT` | processed EDI files of lines L18 and L22 | Kouabena et al. (2025) |
| `tables/` | run summary of the Occam2D lines | this work |
| `rebuild/` | earlier conversions with station tables, synthetic predictions, Tongkeng station file | pyCSAMT examples |

`SHA256SUMS` lists the checksum of every file; `fetch_data.py
--check` re-checks them. Of each Occam2D run, the archive keeps the
mesh, model, startup, log, every iteration file and, where public,
the data file and final response; console logs are left out.

## Restricted Baohuashan data

Only lines L18 and L22 of the Baohuashan AMT survey are public. The
archive holds the inversion models of all five lines and of the 3D
inversion, but no measured data of lines L26, L30 and L34: their EDI
files, the Occam2D data files and responses, and the data files of
the two ModEM runs (which hold all stations of the survey) are left
out and listed in `RESTRICTED.txt`. The complete data are available
from the authors on reasonable request. Without them, tier 1
reproduces every result of the paper; tier 2 rebuilds the models of
L18, L22, Tongkeng, MARE2DEM and the synthetic predictions, and takes
the other Baohuashan models and their inversion records from
`models/`.

## EMC models

The three EMC models are redistributed unchanged so that the round
trip of the paper can be repeated offline. The original products are
openly available from EarthScope:

- EMC-MCR-MT-2016, doi:10.17611/dp/emc.2023.mcrmt.2016.1
- EMC-THO-MT-2021, doi:10.17611/dp/emc.2021.thomt.1
- EMC-WUS-MT-2021, doi:10.17611/dp/emc.2021.wusmt.1

Please cite these products and the associated publications
(Bedrosian, 2016; Bedrosian and Finn, 2021; Murphy et al., 2023)
when using them.

## Acknowledgment

We thank Rujun Chen, leader of GSAI Geophysics Ltd, for permission
to use the Baohuashan data for testing and for the advancement of
science.

## Licence

Files produced for this work (models, tables, conversions) are
released under the Creative Commons Attribution 4.0 International
licence (CC BY 4.0). Files from third parties (EMC products, the
MARE2DEM demonstration, the pyCSAMT sample data) remain under the
terms of their original distribution.
