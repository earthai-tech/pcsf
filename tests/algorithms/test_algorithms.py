"""Tests for pcsf.algorithms.

Covers sampling, location, comparison, uncertainty, projection,
registration and regridding.
"""

import numpy as np
import pytest

from pcsf import (
    Grid2DGeometry,
    Grid3DGeometry,
    PCSFModel,
    UnstructuredMeshGeometry,
)
from pcsf.algorithms import (
    TriangleLocator,
    compare_log10,
    decompose_frame,
    encoding_jacobian,
    interpolated_std,
    interpolation_weights,
    log_uncertainty,
    lognormal_relative_std,
    mesh_to_grid2d,
    node_to_cell,
    register_frame,
    sample_log10,
    transform_covariance,
)
from pcsf.exceptions import EncodingError, GeometryError


def _grid2d():
    return PCSFModel(
        geometry=Grid2DGeometry(x=[0.0, 10.0, 20.0], z=[5.0, 15.0]),
        resistivity=10.0
        ** np.array([[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]]),
    )


def _two_triangles():
    geo = UnstructuredMeshGeometry(
        nodes=np.array(
            [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
        ),
        connectivity=np.array([[0, 1, 2], [1, 3, 2]]),
        region_ids=np.array([0, 1]),
    )
    return PCSFModel(geometry=geo, resistivity=np.array([10.0, 100.0]))


# ------------------------------------------------------------------
# sampling
def test_grid2d_linear_between_centres():
    np.testing.assert_allclose(
        sample_log10(_grid2d(), [[5.0, 10.0], [15.0, 5.0]]), [1.5, 2.5]
    )


def test_grid2d_half_cell_edge_and_outside():
    out = sample_log10(
        _grid2d(),
        [[0.0, 0.0], [25.0, 10.0], [26.0, 10.0], [10.0, 25.0]],
    )
    np.testing.assert_allclose(out[:2], [1.0, 3.0])
    assert np.isnan(out[2]) and np.isnan(out[3])


def test_grid2d_explicit_nodes():
    geo = Grid2DGeometry(
        x=[0.0, 10.0],
        z=[5.0],
        x_nodes=[-50.0, 5.0, 15.0],
        z_nodes=[0.0, 10.0],
    )
    m = PCSFModel(
        geometry=geo, resistivity=10.0 ** np.array([[1.0, 2.0]])
    )
    out = sample_log10(m, [[-40.0, 5.0], [-60.0, 5.0]])
    assert out[0] == pytest.approx(1.0) and np.isnan(out[1])


def test_grid_descending_axis_matches_ascending():
    asc = PCSFModel(
        geometry=Grid2DGeometry(x=[0.0, 10.0, 20.0], z=[5.0]),
        resistivity=10.0 ** np.array([[1.0, 2.0, 4.0]]),
    )
    desc = PCSFModel(
        geometry=Grid2DGeometry(x=[20.0, 10.0, 0.0], z=[5.0]),
        resistivity=10.0 ** np.array([[4.0, 2.0, 1.0]]),
    )
    pts = [[3.0, 5.0], [12.0, 5.0], [19.0, 5.0]]
    np.testing.assert_allclose(
        sample_log10(asc, pts), sample_log10(desc, pts)
    )


def test_grid3d_trilinear_centre_is_mean():
    m = PCSFModel(
        geometry=Grid3DGeometry(
            x=[0.0, 10.0], y=[0.0, 10.0], z=[5.0, 15.0]
        ),
        resistivity=10.0 ** np.arange(8.0).reshape(2, 2, 2),
    )
    assert sample_log10(m, [[5.0, 5.0, 10.0]])[0] == pytest.approx(3.5)


def test_grid3d_matches_scipy_reference():
    scipy = pytest.importorskip("scipy.interpolate")
    rng = np.random.default_rng(0)
    x, y, z = (
        np.sort(rng.uniform(0, 100, 7)),
        np.sort(rng.uniform(0, 50, 5)),
        np.sort(rng.uniform(0, 30, 4)),
    )
    v = rng.uniform(0, 4, (z.size, y.size, x.size))
    m = PCSFModel(
        geometry=Grid3DGeometry(x=x, y=y, z=z), resistivity=10.0**v
    )
    pts = np.column_stack(
        [
            rng.uniform(x[0], x[-1], 500),
            rng.uniform(y[0], y[-1], 500),
            rng.uniform(z[0], z[-1], 500),
        ]
    )
    ref = scipy.RegularGridInterpolator((z, y, x), v)(pts[:, ::-1])
    np.testing.assert_allclose(
        sample_log10(m, pts), ref, rtol=0, atol=1e-12
    )


def test_mesh_point_location():
    out = sample_log10(
        _two_triangles(), [[0.2, 0.2], [0.8, 0.8], [2.0, 2.0]]
    )
    np.testing.assert_allclose(out[:2], [1.0, 2.0])
    assert np.isnan(out[2])


def test_wrong_point_dimension_raises():
    with pytest.raises(GeometryError):
        sample_log10(_grid2d(), [[0.0, 0.0, 0.0]])


# ------------------------------------------------------------------
# locate
def test_locator_matches_matplotlib_on_random_mesh():
    tri_mod = pytest.importorskip("matplotlib.tri")
    rng = np.random.default_rng(1)
    pts = rng.uniform(0, 1, (400, 2))
    t = tri_mod.Triangulation(pts[:, 0], pts[:, 1])
    q = rng.uniform(-0.1, 1.1, (5000, 2))
    ours = TriangleLocator(pts, t.triangles)(q)
    ref = t.get_trifinder()(q[:, 0], q[:, 1])
    # points exactly on shared edges may be assigned to either
    # neighbour
    agree = (ours == ref) | ((ours >= 0) & (ref >= 0))
    assert agree.all()
    assert np.array_equal(ours >= 0, ref >= 0)


def test_locator_outside_bbox_is_minus_one():
    m = _two_triangles()
    loc = TriangleLocator(m.geometry.nodes, m.geometry.connectivity)
    assert (loc([[5.0, 5.0], [-1.0, 0.5]]) == -1).all()


# ------------------------------------------------------------------
# comparison
def test_compare_statistics_ignore_nan():
    res = compare_log10([1.0, 2.0, np.nan, 4.0], [1.5, 2.0, 3.0, 4.5])
    assert res.n == 3
    assert res.bias == pytest.approx(-1.0 / 3.0)
    assert res.rms == pytest.approx(np.sqrt(0.5 / 3.0))


def test_compare_shape_mismatch():
    with pytest.raises(GeometryError):
        compare_log10([1.0, 2.0], [1.0])


# ------------------------------------------------------------------
# uncertainty
def test_log_uncertainty():
    assert log_uncertainty(0.1, "log10", "ln") == pytest.approx(
        0.1 * np.log(10)
    )
    s = log_uncertainty(0.01, "log10", "linear", rho=100.0)
    assert s == pytest.approx(100.0 * np.log(10) * 0.01)
    assert log_uncertainty(
        s, "linear", "log10", rho=100.0
    ) == pytest.approx(0.01)
    with pytest.raises(EncodingError):
        log_uncertainty(0.1, "log10", "linear")


def test_lognormal_vs_first_order():
    exact = lognormal_relative_std([0.05, 0.2])
    first = np.log(10) * np.array([0.05, 0.2])
    np.testing.assert_allclose(
        (first - exact) / exact, [-0.0099, -0.1479], atol=5e-4
    )


def test_transform_covariance_matches_diagonal_rule():
    rho = np.array([10.0, 100.0])
    cov = np.diag([0.01, 0.04])  # log10 variances
    cy = transform_covariance(cov, rho, "log10", "linear")
    np.testing.assert_allclose(
        np.sqrt(np.diag(cy)),
        log_uncertainty(
            np.sqrt(np.diag(cov)), "log10", "linear", rho=rho
        ),
    )
    np.testing.assert_allclose(
        encoding_jacobian(rho, "log10", "ln"), np.log(10)
    )


def test_interpolated_std_independent_and_full_cov():
    m = _grid2d()
    w = interpolation_weights(m, [[5.0, 10.0]])
    sigma = np.full((2, 3), 0.1)
    s_ind = interpolated_std(w, sigma=sigma)[0]
    assert s_ind == pytest.approx(
        0.1 * np.sqrt(4 * 0.25**2)
    )  # four equal weights
    s_full = interpolated_std(w, cov=np.full((6, 6), 0.01))[
        0
    ]  # fully correlated
    assert s_full == pytest.approx(0.1)


# ------------------------------------------------------------------
# projection
def test_node_to_cell():
    conn = np.array([[0, 1, 2]])
    rho = np.array([10.0, 100.0, 1000.0])
    assert node_to_cell(conn, rho, "arithmetic")[0] == pytest.approx(
        370.0
    )
    assert node_to_cell(conn, rho, "geometric")[0] == pytest.approx(
        100.0
    )
    with pytest.raises(GeometryError):
        node_to_cell(conn, rho, "median")


# ------------------------------------------------------------------
# registration
def test_register_and_decompose_north_first_frame():
    rng = np.random.default_rng(2)
    u = rng.uniform(0, 5000, (30, 2))  # easting, northing
    theta = np.radians(3.0)
    R = np.array(
        [
            [np.cos(theta), -np.sin(theta)],
            [np.sin(theta), np.cos(theta)],
        ]
    )
    P = np.array([[0.0, 1.0], [1.0, 0.0]])
    A = R @ P
    g = u @ A.T + np.array([100.0, -50.0])
    reg = register_frame(u, g)
    assert reg.rms_residual < 1e-8
    d = decompose_frame(reg.A)
    assert d["permuted"] and d["rotation_deg"] == pytest.approx(3.0)
    np.testing.assert_allclose(d["scales"], [1.0, 1.0])


# ------------------------------------------------------------------
# regrid
def test_mesh_to_grid2d_is_synthesized():
    g = mesh_to_grid2d(_two_triangles(), nx=11, nz=11)
    assert g.kind == "grid2d" and g.metadata["synthesized"] is True
    assert (
        np.nanmin(g.resistivity) == 10.0
        and np.nanmax(g.resistivity) == 100.0
    )
