# Zenodo record of the paper data (author checklist)

Create a **new upload** (not a new version of the pyCSAMT record
10.5281/zenodo.22160713) and reserve its DOI. Fill the fields below,
upload `paper/pcsf-paper-data-1.zip`, check the checksum and publish.
Then write the DOI and record id into `paper/data_source.json` and
into the `PCSFdata` entry of `manuscript/pcsf.bib`.

## Files

| File | Size | SHA-256 |
|---|---|---|
| `pcsf-paper-data-1.zip` | 78.2 MB | `13cc3b8470d3979d9052dfc6c61f59080e43d519e71eec744df897c317ae9cc6` |

## Basic information

- **Resource type:** Dataset
- **Title:** Data archive for "A geometry-aware exchange format for
  electromagnetic inversion models" (PCSF paper data, version 1)
- **Publication date:** date of publication
- **Creators:** Kouadio, Kouao Laurent (ORCID 0000-0001-7259-7254);
  affiliation as in your other records
- **Version:** 1
- **Language:** English
- **Licence:** Creative Commons Attribution 4.0 International
  (CC BY 4.0). Third-party files keep their original terms (see the
  description).
- **Access:** open; for the review period, use restricted access
  with a share link if double-anonymous review requires it

## Description (paste as is)

> Data needed to reproduce every number, table and figure of the
> manuscript "A geometry-aware exchange format for electromagnetic
> inversion models", which introduces the Portable Common Subsurface
> Format (PCSF) for electromagnetic inversion models.
>
> The archive holds (1) the 14 inversion models of the paper in PCSF
> (HDF5) and in its text encoding PCSM; (2) the native solver files
> they were converted from: Occam2D runs of the Tongkeng CSAMT profile
> and of five Baohuashan AMT lines, two ModEM 3D runs of the
> Baohuashan survey, and the MARE2DEM demonstration inversion; (3) the
> processed EDI files of Baohuashan lines L18 and L22; (4) three
> models of the EarthScope Earth Model Collaboration (EMC-MCR-MT-2016,
> EMC-THO-MT-2021, EMC-WUS-MT-2021) as netCDF files with the ModEM
> models they derive from; and (5) tables and earlier conversions used
> by the rebuild. `SHA256SUMS` lists every file.
>
> The code that reads the archive is the `paper/` folder of the pcsf
> package: `fetch_data.py` unpacks and checks the archive,
> `run_all.py` runs all analyses with pcsf alone, `run_all.py
> --rebuild` first rebuilds the models from the native runs with
> pyCSAMT, and `check_results.py` compares the output with the values
> reported in the paper.
>
> Restricted data. Only lines L18 and L22 of the Baohuashan survey
> are public. The archive holds the inversion models of all five
> lines and of the 3D inversion, but not the measured data of lines
> L26, L30 and L34: their EDI files, Occam2D data files and responses,
> and the data files of the two ModEM runs (which hold all stations)
> are listed in `RESTRICTED.txt` and are available from the author on
> reasonable request. Every result of the paper can be reproduced
> without them.
>
> The EMC models are redistributed unchanged for offline
> reproduction; the original products are openly available from
> EarthScope (doi:10.17611/dp/emc.2023.mcrmt.2016.1,
> doi:10.17611/dp/emc.2021.thomt.1, doi:10.17611/dp/emc.2021.wusmt.1)
> and should be cited when used.
>
> We thank Rujun Chen, leader of GSAI Geophysics Ltd, for permission
> to use the Baohuashan data to test the format and for the
> advancement of science.
>
> Licence: files produced for this work are released under CC BY 4.0;
> third-party files (EMC products, the MARE2DEM demonstration, the
> pyCSAMT sample run) remain under the terms of their original
> distribution.

## Keywords

electromagnetic geophysics; magnetotellurics; audio-magnetotellurics;
CSAMT; inversion model; data format; HDF5; PCSF; FAIR data;
reproducibility; Occam2D; ModEM; MARE2DEM

## Related works

| Relation | Identifier | Resource type |
|---|---|---|
| Is supplement to | DOI of the Geophysics paper (after acceptance) | Publication / article |
| Is compiled by | https://github.com/earthai-tech/pcsf (once public) | Software |
| Is compiled by | 10.5281/zenodo.22160713 (pyCSAMT v2.5.1) | Software |
| References | 10.1016/j.oregeorev.2025.106798 (Baohuashan survey) | Publication / article |
| References | 10.1016/j.jappgeo.2020.104204 (Tongkeng survey) | Publication / article |
| References | 10.1016/j.jappgeo.2022.104647 (pyCSAMT) | Publication / article |
| References | 10.17611/dp/emc.2023.mcrmt.2016.1 | Dataset |
| References | 10.17611/dp/emc.2021.thomt.1 | Dataset |
| References | 10.17611/dp/emc.2021.wusmt.1 | Dataset |

## About the reserved DOI 10.5281/zenodo.24105024

That DOI belongs to a draft new version of the pyCSAMT software
record (concept 10.5281/zenodo.22160712). A reserved DOI cannot be
moved to another upload. Either use that draft for the next pyCSAMT
release (for example the version with the pcsf shim), or discard it;
the paper data get the DOI reserved in the new dataset upload.

## Still to confirm before publishing

- Agreement of the author of the Baohuashan ModEM model to its
  release.
- Terms of the MARE2DEM demonstration files and of the pyCSAMT
  sample run.
