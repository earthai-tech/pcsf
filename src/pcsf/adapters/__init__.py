"""Conversion of solver output to PCSF models.

Each adapter reads native files through :mod:`pcsf.native` and
registers itself in :data:`pcsf.api.registry.ADAPTERS`, so that
``ADAPTERS.get("occam2d")`` returns :func:`occam2d_to_pcsf`.
Third-party solvers plug in through the ``pcsf.adapters``
entry-point group (see :mod:`pcsf.plugins`).

========== ======================== =====================
Name       Function                 Geometry kind
========== ======================== =====================
occam2d    :func:`occam2d_to_pcsf`  ``grid2d``
modem      :func:`modem_to_pcsf`    ``grid3d``
mare2dem   :func:`mare2dem_to_pcsf` ``mesh_unstructured``
emc        :func:`emc_to_pcsf`      ``grid3d`` (geographic)
========== ======================== =====================

:func:`pcsf.adapters.emc.pcsf_to_emc` writes an EMC model back to
netCDF. MARE2DEM triangulation needs ``pcsf[mare2dem]`` and EMC files
need ``pcsf[emc]``; both are imported only when used.

Examples
--------
>>> from pcsf.api.registry import ADAPTERS
>>> import pcsf.adapters
>>> ADAPTERS.names()
('emc', 'mare2dem', 'modem', 'occam2d')
"""

from .emc import emc_to_pcsf, pcsf_to_emc
from .mare2dem import mare2dem_to_pcsf
from .modem import modem_to_pcsf
from .occam2d import occam2d_to_pcsf

__all__ = [
    "emc_to_pcsf",
    "mare2dem_to_pcsf",
    "modem_to_pcsf",
    "occam2d_to_pcsf",
    "pcsf_to_emc",
]
