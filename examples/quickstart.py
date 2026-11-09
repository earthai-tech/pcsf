"""Build a model, write both encodings, validate and sample it."""

import numpy as np

import pcsf
from pcsf.algorithms import sample_log10

rho = np.array([[100.0, 300.0, 1000.0], [50.0, 200.0, 800.0]])
native = np.log10(rho)
model = pcsf.PCSFModel(
    geometry=pcsf.Grid2DGeometry(
        x=[0.0, 100.0, 200.0], z=[25.0, 75.0]
    ),
    resistivity=10.0**native,
    resistivity_native=native,
    resistivity_native_encoding="log10",
    source_backend="example",
)
pcsf.write(model, "example.pcsf")
pcsf.write(model, "example.pcsm")
print(pcsf.validate("example.pcsm"))
print(sample_log10(model, [[50.0, 50.0], [150.0, 30.0]]))
