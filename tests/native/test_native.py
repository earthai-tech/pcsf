"""Tests for the native parsers on the bundled tiny runs."""

import numpy as np
import pytest

import pcsf
from pcsf.exceptions import FormatError
from pcsf.native import mare2dem, modem, occam2d

OCC = pcsf.datasets.path("occam2d_tiny")
MOD = pcsf.datasets.path("modem_tiny")
M2D = pcsf.datasets.path("mare2dem_tiny")


# ------------------------------------------------------------------
# Occam2D
def test_occam_mesh_widths_nodes_and_air():
    mesh = occam2d.read_mesh(OCC / "Occam2DMesh")
    assert mesh.x_widths.shape == (8,) and mesh.z_widths.shape == (4,)
    assert mesh.n_air == 1
    np.testing.assert_array_equal(
        mesh.z_nodes, [0.0, 1000.0, 1010.0, 1030.0, 1070.0]
    )


def test_occam_model_layers():
    model = occam2d.read_model(OCC / "Occam2DModel")
    assert model.mesh_file == "Occam2DMesh"
    assert [n for n, _ in model.layers] == [1, 1, 1]
    assert model.n_params == 7


def test_occam_iteration_and_grid():
    it = occam2d.read_iteration(OCC / "ITER02.iter")
    assert it.iteration == 2 and it.misfit == pytest.approx(1.5)
    assert it.model_file == "Occam2DModel"
    grid = occam2d.resistivity_grid(
        it.values,
        occam2d.read_model(OCC / "Occam2DModel"),
        occam2d.read_mesh(OCC / "Occam2DMesh"),
    )
    assert grid.shape == (4, 8)
    assert np.isnan(grid[0]).all()  # air row
    np.testing.assert_array_equal(grid[3], np.full(8, 3.1))
    np.testing.assert_array_equal(grid[2, :4], 1.9)


def test_occam_iteration_pads_truncated_vector(tmp_path):
    p = tmp_path / "ITER9.iter"
    p.write_text("Format: OCCAMITER_FLEX\nParam Count: 3\n1.0 2.0\n")
    vals = occam2d.read_iteration(p).values
    assert vals[:2].tolist() == [1.0, 2.0] and np.isnan(vals[2])


def test_occam_data_and_log():
    data = occam2d.read_data(OCC / "OccamDataFile.dat")
    assert data.sites == ["S01", "S02", "S03"]
    np.testing.assert_array_equal(data.offsets, [0.0, 50.0, 100.0])
    log = occam2d.read_log(OCC / "LogFile.logfile")
    np.testing.assert_array_equal(log.iteration, [1, 2])
    np.testing.assert_allclose(log.rms, [3.0, 1.5])
    np.testing.assert_allclose(log.lagrange, [2.0, 1.0])
    assert not log.converged


@pytest.mark.parametrize(
    ("reader", "text"),
    [
        (occam2d.read_model, "Format: WRONG\nNum Layers: 0\n"),
        (occam2d.read_iteration, "Format: WRONG\n"),
        (occam2d.read_data, "FORMAT: WRONG\nSITES: 0\n"),
        (occam2d.read_mesh, "only one line\n"),
    ],
)
def test_occam_rejects_bad_files(tmp_path, reader, text):
    p = tmp_path / "bad"
    p.write_text(text)
    with pytest.raises(FormatError):
        reader(p)


def test_missing_file_is_format_error(tmp_path):
    with pytest.raises(FormatError, match="not found"):
        occam2d.read_mesh(tmp_path / "nope")


# ------------------------------------------------------------------
# ModEM
def test_modem_model_orientation_and_trailer():
    m = modem.read_model(MOD / "tiny_NLCG_002.rho")
    assert m.log_rho.shape == (3, 4, 5)
    np.testing.assert_array_equal(m.origin, [-175.0, -150.0, 0.0])
    # The air corner was written at the two southernmost x cells
    # of the first row, which the reader must put at x = 0, 1.
    assert np.allclose(m.log_rho[0, 0, :2], np.log(1e12))


def test_modem_model_log10_and_linear(tmp_path):
    base = "# h\n1 1 1 0 {t}\n10\n10\n10\n{v}\n"
    p = tmp_path / "a.rho"
    p.write_text(base.format(t="LOG10", v="2.0"))
    assert modem.read_model(p).log_rho[0, 0, 0] == pytest.approx(
        2.0 * np.log(10.0)
    )
    p.write_text(base.format(t="LINEAR", v="-1.0"))
    assert np.isnan(modem.read_model(p).log_rho[0, 0, 0])


def test_modem_model_truncated(tmp_path):
    p = tmp_path / "a.rho"
    p.write_text("# h\n2 2 1 0 LOGE\n1 1\n1 1\n1\n0.0 0.0\n")
    with pytest.raises(FormatError, match="expected"):
        modem.read_model(p)


def test_modem_data_and_log():
    d = modem.read_data(MOD / "tiny.dat")
    assert d.sites == ["A01", "A02"]
    np.testing.assert_array_equal(d.xyz[:, 2], [5.0, 12.0])
    assert "depth below 300 m a.s.l." in d.comment
    log = modem.read_log(MOD / "tiny_NLCG.log")
    np.testing.assert_array_equal(log.iteration, [0, 1, 2])
    np.testing.assert_allclose(log.rms, [9.5, 4.2, 1.9])


def test_modem_data_without_rows(tmp_path):
    p = tmp_path / "d.dat"
    p.write_text("# nothing\n")
    with pytest.raises(FormatError):
        modem.read_data(p)


# ------------------------------------------------------------------
# MARE2DEM
def test_mare2dem_resistivity_poly_log():
    r = mare2dem.read_resistivity(M2D / "tiny.1.resistivity")
    np.testing.assert_array_equal(r.rho[:, 0], [1e12, 45.0])
    np.testing.assert_array_equal(r.free[:, 0], [0, 1])
    assert r.misfit == pytest.approx(1.05)
    poly = mare2dem.read_poly(M2D / "tiny.poly")
    assert poly.nodes.shape == (6, 2) and poly.regions.shape == (2, 4)
    log = mare2dem.read_log(M2D / "tiny.logfile")
    np.testing.assert_allclose(log.rms, [3.2, 1.05])
    assert log.converged


def test_mare2dem_resistivity_errors(tmp_path):
    p = tmp_path / "a.resistivity"
    p.write_text("Format: MARE2DEM_1.1\n")
    with pytest.raises(FormatError, match="Number of regions"):
        mare2dem.read_resistivity(p)
    p.write_text("Number of regions: 2\n1 10 1 0 0 0 0\n")
    with pytest.raises(FormatError, match="expected 2"):
        mare2dem.read_resistivity(p)


def test_mare2dem_triangulation_matches_regions():
    pytest.importorskip("triangle")
    nodes, tri, ids = mare2dem.triangulate_poly(
        mare2dem.read_poly(M2D / "tiny.poly")
    )
    assert tri.shape[1] == 3 and set(ids.tolist()) == {1, 2}
    # Region 1 (air) lies at negative z, region 2 at positive z.
    centroid_z = nodes[tri].mean(axis=1)[:, 1]
    assert (centroid_z[ids == 1] < 0).all()
    assert (centroid_z[ids == 2] > 0).all()
