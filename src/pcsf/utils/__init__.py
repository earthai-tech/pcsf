"""Small helpers shared by several modules, one theme per module.

A helper used by a single module stays in that module; it moves here
when a second module needs it.

Modules
-------
arrays
    Dimension and shape checks, float conversion.
io
    Suffixes, gzip detection, text opening, atomic writes.
hashing
    SHA-256 of files and arrays.
text
    Shortest round-trip float formatting.
geo
    Affine fits and coordinate transformations (the latter needs
    ``pcsf[geo]``).
"""
