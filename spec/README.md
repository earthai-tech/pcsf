# Specification

| File | Content |
|---|---|
| `pcsf-0.1.md` | specification of format version 0.1.0 (data model, HDF5 layout, PCSM, versioning) |
| `pcsm.ebnf` | grammar of the PCSM text encoding |
| `schema/` | JSON Schema of the HDF5 layout (planned for 0.2.0) |

The format version (`FORMAT_VERSION`, written as `pcsf_version` /
`PCSM_VERSION`) is independent of the package version. Minor versions
add optional fields, kinds or encodings and stay readable by older
readers; major versions change existing fields. Proposals go through an
issue labelled `spec`.
