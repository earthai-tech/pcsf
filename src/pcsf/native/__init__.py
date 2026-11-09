"""Pure parsers of solver files (planned for phase 2).

Each module will read one solver's native files with NumPy only, so
that pcsf converts solver output without depending on any inversion
package:

- ``occam2d``  -- Occam2D mesh, model, iteration and data files
- ``modem``    -- ModEM ``.rho`` models and ``.dat`` data files
- ``mare2dem`` -- MARE2DEM ``.resistivity`` and ``.poly`` files
- ``emc``      -- EarthScope / IRIS Earth Model Collaboration netCDF
  files
"""
