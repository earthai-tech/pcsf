"""Tests for the EMC netCDF adapter (needs netCDF4)."""

import numpy as np
import pytest

import pcsf
from pcsf.adapters.emc import emc_to_pcsf, pcsf_to_emc
from pcsf.exceptions import AdapterError

netCDF4 = pytest.importorskip("netCDF4")


@pytest.fixture
def emc_file(tmp_path):
    path = tmp_path / "toy.nc"
    with netCDF4.Dataset(path, "w", format="NETCDF4_CLASSIC") as d:
        d.createDimension("depth", 2)
        d.createDimension("latitude", 3)
        d.createDimension("longitude", 4)
        for name, vals in (
            ("longitude", [-113.0, -112.9, -112.8, -112.7]),
            ("latitude", [40.0, 40.1, 40.2]),
            ("depth", [1.0, 5.5]),
        ):
            v = d.createVariable(name, "f4", (name,))
            v.units = "km" if name == "depth" else "degrees"
            v[:] = vals
        v = d.createVariable(
            "log10sigma",
            "f4",
            ("depth", "latitude", "longitude"),
            fill_value=np.float32(99999.0),
        )
        v.long_name = "log10 of conductivity"
        v.units = "log10(S/m)"
        data = np.linspace(-3.0, -1.0, 24, dtype=np.float32)
        data = data.reshape(2, 3, 4)
        data[0, 0, 0] = 99999.0
        v[:] = data
        d.id = "toy"
        d.title = "toy model"
        d.year = np.int32(2021)
    return path


def test_emc_round_trip_is_lossless(emc_file, tmp_path):
    model = emc_to_pcsf(emc_file)
    assert model.resistivity_native_encoding == "log10_conductivity"
    assert model.resistivity.shape == (2, 3, 4)
    assert np.isnan(model.resistivity[0, 0, 0])
    np.testing.assert_array_equal(model.geometry.z, [1000.0, 5500.0])
    assert pcsf.validate(model).passed
    back = pcsf.read(pcsf.write(model, tmp_path / "m.pcsm.gz"))
    out = pcsf_to_emc(back, tmp_path / "copy.nc")
    with netCDF4.Dataset(emc_file) as a, netCDF4.Dataset(out) as b:
        a.set_auto_mask(False)
        b.set_auto_mask(False)
        assert a.data_model == b.data_model
        for name in a.variables:
            assert a[name].dtype == b[name].dtype
            np.testing.assert_array_equal(a[name][:], b[name][:])
            assert a[name].ncattrs() == b[name].ncattrs() or set(
                a[name].ncattrs()
            ) == set(b[name].ncattrs())
        assert b.getncattr("year") == 2021
        assert type(b.getncattr("year")) is type(a.getncattr("year"))


def test_emc_resistivity_values(emc_file):
    model = emc_to_pcsf(emc_file)
    np.testing.assert_allclose(
        model.resistivity[1], 10.0 ** -model.resistivity_native[1]
    )


def test_pcsf_to_emc_needs_emc_metadata(tmp_path):
    model = pcsf.PCSFModel(
        geometry=pcsf.Grid2DGeometry(x=[0.0], z=[1.0]),
        resistivity=[[1.0]],
    )
    with pytest.raises(AdapterError, match="EMC metadata"):
        pcsf_to_emc(model, tmp_path / "x.nc")


def test_emc_rejects_wrong_dimensions(tmp_path):
    path = tmp_path / "bad.nc"
    with netCDF4.Dataset(path, "w") as d:
        for n in ("a", "b", "c"):
            d.createDimension(n, 1)
        d.createVariable("v", "f4", ("a", "b", "c"))[:] = 1.0
    with pytest.raises(AdapterError, match="dimensions"):
        emc_to_pcsf(path)
