"""Tests for the adapters, including parity with pyCSAMT."""

import warnings

import numpy as np
import pytest

import pcsf
from pcsf.adapters import (
    mare2dem_to_pcsf,
    modem_to_pcsf,
    occam2d_to_pcsf,
)
from pcsf.adapters.modem import mask_air, station_elevation
from pcsf.adapters.occam2d import chainage_shift
from pcsf.api.registry import ADAPTERS
from pcsf.exceptions import AdapterError, GeometryError

OCC = pcsf.datasets.path("occam2d_tiny")
MOD = pcsf.datasets.path("modem_tiny")
M2D = pcsf.datasets.path("mare2dem_tiny")


def _tiny_mesh():
    nodes = np.loadtxt(M2D / "tiny.node.txt")
    tri = np.loadtxt(M2D / "tiny.ele.txt", dtype=int)
    return nodes, tri[:, :3], tri[:, 3]


def _modem(**kw):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return modem_to_pcsf(
            MOD / "tiny_NLCG_002.rho",
            data=MOD / "tiny.dat",
            log=MOD / "tiny_NLCG.log",
            **kw,
        )


def test_registry_lists_adapters():
    assert ADAPTERS.get("occam2d") is occam2d_to_pcsf
    assert ADAPTERS.get("modem") is modem_to_pcsf
    assert ADAPTERS.get("mare2dem") is mare2dem_to_pcsf
    assert ADAPTERS.names() == ("emc", "mare2dem", "modem", "occam2d")


# ------------------------------------------------------------------
# Occam2D
def test_occam2d_model_is_conforming_and_round_trips(tmp_path):
    model = occam2d_to_pcsf(
        OCC,
        station_lonlat={"S01": (117.0, 25.0)},
        station_elevations={"S02": 310.0},
    )
    assert pcsf.validate(model).passed
    assert model.metadata["iteration_file"] == "ITER02.iter"
    assert model.metadata["final_rms"] == pytest.approx(1.5)
    assert np.isnan(model.stations.lon[1])
    assert model.topography.elevation[1] == 310.0
    back = pcsf.read(pcsf.write(model, tmp_path / "o.pcsm"))
    np.testing.assert_array_equal(
        back.resistivity_native, model.resistivity_native
    )


def test_occam2d_stations_lie_inside_the_core():
    model = occam2d_to_pcsf(OCC)
    x = model.geometry.x_nodes
    # 800 m mesh: 350 m of padding on each side of a 100 m core.
    assert x[0] == pytest.approx(-350.0)
    assert x[-1] == pytest.approx(450.0)


def test_occam2d_selects_iteration():
    model = occam2d_to_pcsf(OCC, iteration=1)
    assert model.metadata["final_rms"] == pytest.approx(3.0)
    with pytest.raises(AdapterError, match="no iteration"):
        occam2d_to_pcsf(OCC, iteration=7)


def test_occam2d_errors(tmp_path):
    with pytest.raises(AdapterError, match="not a folder"):
        occam2d_to_pcsf(tmp_path / "missing")
    with pytest.raises(AdapterError, match=r"no Occam2D \*\.iter"):
        occam2d_to_pcsf(tmp_path)
    (tmp_path / "ITER01.iter").write_text(
        "Format: OCCAMITER_FLEX\nModel File: absent\nParam Count: 0\n"
    )
    with pytest.raises(AdapterError, match="model file"):
        occam2d_to_pcsf(tmp_path)


def test_chainage_shift_single_station():
    assert chainage_shift([0.0, 10.0], [5.0]) == 0.0


# ------------------------------------------------------------------
# ModEM
def test_modem_masks_air_and_keeps_source_values():
    model = _modem()
    assert int(np.isnan(model.resistivity).sum()) == 2
    assert np.isfinite(model.resistivity_native).all()
    assert model.metadata["air_mask"]["n_cells_masked"] == 2
    assert pcsf.validate(model).passed


def test_modem_unmasked_and_elevation_convention():
    model = _modem(
        air_threshold_ohm_m=None, station_z_convention="elevation"
    )
    assert not np.isnan(model.resistivity).any()
    np.testing.assert_array_equal(model.stations.z, [5.0, 12.0])
    assert "air_mask" not in model.metadata


def test_modem_depth_column_is_converted_with_warning():
    with pytest.warns(UserWarning, match="depth"):
        model = modem_to_pcsf(
            MOD / "tiny_NLCG_002.rho", data=MOD / "tiny.dat"
        )
    np.testing.assert_array_equal(model.stations.z, [295.0, 288.0])
    assert model.metadata["station_z"]["datum_masl"] == 300.0


def test_modem_history_and_model_only():
    model = _modem()
    assert model.metadata["n_iter"] == 3
    assert model.metadata["final_rms"] == pytest.approx(1.9)
    alone = modem_to_pcsf(MOD / "tiny_NLCG_002.rho")
    assert alone.stations is None and alone.history == {}


def test_station_elevation_rules():
    z, info = station_elevation([0.0, 0.0], "z is depth")
    assert not info["flipped"]  # all-zero column is kept
    z, info = station_elevation([10.0, 30.0], "positive down")
    np.testing.assert_array_equal(z, [20.0, 0.0])
    assert info["datum_masl"] is None
    z, _ = station_elevation([10.0], "no hint")
    assert z.tolist() == [10.0]
    with pytest.raises(ValueError, match="convention"):
        station_elevation([1.0], "", "upward")


def test_mask_air_keeps_existing_nan():
    masked, n_air = mask_air(np.full((1, 1, 2), np.nan), 1e8)
    assert n_air == 0 and np.isnan(masked).all()


# ------------------------------------------------------------------
# MARE2DEM
def test_mare2dem_with_explicit_mesh():
    model = mare2dem_to_pcsf(
        M2D / "tiny.1.resistivity",
        mesh=_tiny_mesh(),
        log=M2D / "tiny.logfile",
    )
    np.testing.assert_array_equal(
        model.resistivity, [1e12, 1e12, 45.0, 45.0]
    )
    assert model.metadata["iteration"] == 1
    assert model.metadata["converged"] is True
    assert pcsf.validate(model).passed


def test_mare2dem_from_poly_needs_triangle():
    pytest.importorskip("triangle")
    model = mare2dem_to_pcsf(M2D / "tiny.1.resistivity")
    assert set(model.resistivity.tolist()) == {1e12, 45.0}


def test_mare2dem_rejects_bad_regions_and_anisotropy(tmp_path):
    nodes, tri, ids = _tiny_mesh()
    with pytest.raises(GeometryError, match="region ids"):
        mare2dem_to_pcsf(
            M2D / "tiny.1.resistivity", mesh=(nodes, tri, ids + 5)
        )
    p = tmp_path / "x.1.resistivity"
    p.write_text(
        "Anisotropy: triaxial\nNumber of regions: 1\n"
        "1 1 1 1 0 0 0 0 0 0 0\n"
    )
    with pytest.raises(AdapterError, match="isotropic"):
        mare2dem_to_pcsf(p, mesh=(nodes, tri, ids))


# ------------------------------------------------------------------
# Parity with pyCSAMT, the reference implementation
def _same(a, b):
    return np.array_equal(
        np.asarray(a, float), np.asarray(b, float), equal_nan=True
    )


def test_occam2d_parity_with_pycsamt():
    adapters = pytest.importorskip("pycsamt.format.adapters")
    result = pytest.importorskip(
        "pycsamt.models.occam2d"
    ).InversionResult(OCC)
    ref = adapters.occam2d_to_pcsf(result)
    ours = occam2d_to_pcsf(OCC)
    for name in ("x", "z", "x_nodes", "z_nodes"):
        assert _same(
            getattr(ours.geometry, name), getattr(ref.geometry, name)
        )
    assert _same(ours.resistivity_native, ref.resistivity_native)
    assert _same(ours.stations.x, ref.stations.x)
    for key, value in ref.history.items():
        assert _same(ours.history[key], value)


def test_modem_parity_with_pycsamt():
    adapters = pytest.importorskip("pycsamt.format.adapters")
    m3d = pytest.importorskip("pycsamt.models.modem.model3d")
    dat = pytest.importorskip("pycsamt.models.modem.data")
    res = pytest.importorskip("pycsamt.models.modem.results")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        ref = adapters.modem3d_to_pcsf(
            res.InversionResult(MOD),
            model=m3d.ModEmModel3D.read(MOD / "tiny_NLCG_002.rho"),
            data=dat.ModEmData.read(MOD / "tiny.dat"),
        )
    ours = _modem()
    assert _same(ours.resistivity, ref.resistivity)
    assert _same(ours.resistivity_native, ref.resistivity_native)
    assert _same(ours.geometry.origin, ref.geometry.origin)
    assert _same(ours.stations.z, ref.stations.z)
    for key, value in ref.history.items():
        assert _same(ours.history[key], value)
