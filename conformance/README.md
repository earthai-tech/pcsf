# Conformance suite

Reference files and expected values that any implementation of PCSF
(Python, MATLAB, Julia, C, ...) can use to prove it reads the format
correctly.

Planned content (phase 2):

- `files/`: small reference models of every geometry kind and encoding,
  in PCSF and PCSM, including edge cases (NaN, padding, per-node values,
  multiline, conductivity encodings);
- `expected.json`: for each file, SHA-256 of the canonical and source
  arrays, shapes, and the expected result of conformance rules C1-C9;
- `run.py`: reference runner.

The 12 files of the Geophysics paper and three EarthScope/IRIS EMC models
already pass the rules with the reference implementation and with three
independent readers.
