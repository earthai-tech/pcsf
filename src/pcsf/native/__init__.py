"""Parsers of solver files, with NumPy as the only dependency.

Each module reads one solver's files so that pcsf converts solver
output without depending on any inversion package. The parsers
follow the rules of pyCSAMT's readers, so that both give
bit-identical arrays.

Modules
-------
occam2d
    Occam2D mesh, model, iteration, data and log files.
modem
    ModEM ``.rho`` models, ``.dat`` station tables and NLCG logs.
mare2dem
    MARE2DEM ``.resistivity`` tables, ``.poly`` graphs and logs;
    triangulation needs ``pcsf[mare2dem]``.
"""

from . import mare2dem, modem, occam2d

__all__ = ["mare2dem", "modem", "occam2d"]
