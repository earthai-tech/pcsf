"""Compatibility layer.

All version-dependent code lives here, so that supporting or dropping
a Python, NumPy or h5py version means editing one module.

Modules
-------
python
    Differences between Python 3.9 and 3.10+.
numpy
    Differences between NumPy 1.x and 2.x.
h5py
    String and attribute handling across h5py versions.
optional
    Lazy imports of optional dependencies.
"""

from .optional import import_optional, is_available

__all__ = ["import_optional", "is_available"]
