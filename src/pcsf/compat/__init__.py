"""Compatibility layer.

All version-dependent code lives here, so that supporting or dropping a
Python, NumPy or h5py version means editing one module:

- :mod:`pcsf.compat.python`  -- Python 3.9 / 3.10+ differences
- :mod:`pcsf.compat.numpy`   -- NumPy 1.x / 2.x differences
- :mod:`pcsf.compat.h5py`    -- string and attribute handling across h5py versions
- :mod:`pcsf.compat.optional` -- lazy imports of optional dependencies
"""

from .optional import import_optional, is_available

__all__ = ["import_optional", "is_available"]
