"""Small helpers shared by several modules, one theme per module.

Rule: a helper used by a single module stays in that module; it moves
here when a second module needs it.

- :mod:`pcsf.utils.arrays`  -- shape checks, NaN handling, dtype casting
- :mod:`pcsf.utils.io`      -- paths, gzip detection, atomic writes
- :mod:`pcsf.utils.hashing` -- SHA-256 of files and arrays
- :mod:`pcsf.utils.text`    -- shortest round-trip float formatting
- :mod:`pcsf.utils.geo`     -- coordinate transformations (needs ``pcsf[geo]``)
"""
