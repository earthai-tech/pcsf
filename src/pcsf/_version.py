"""Version numbers.

Two numbers are kept apart on purpose:

``__version__``
    The version of this Python package (the software).
``FORMAT_VERSION``
    The version of the PCSF/PCSM specification the package writes. It
    follows its own semantic-versioning policy (spec/, section
    "Versioning") and changes only when the file layout changes.
"""

__version__ = "0.1.0"

#: Specification version written to every file (``pcsf_version`` /
#: ``PCSM_VERSION``).
FORMAT_VERSION = "0.1.0"

__all__ = ["FORMAT_VERSION", "__version__"]
