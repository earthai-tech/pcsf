"""Tests of the PCSF Studio parts that need no Qt."""

from pathlib import Path

import numpy as np
import pytest

from pcsf import datasets, read, write
from pcsf.exceptions import FormatError
from pcsf.studio import figures, summary
from pcsf.studio.sources import open_source

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
from matplotlib.figure import Figure  # noqa: E402

FILES = Path(__file__).resolve().parents[2] / "conformance" / "files"


def _models():
    out = {
        n: open_source(datasets.path(n)).model
        for n in datasets.NAMES
        if n != "mare2dem_tiny"
    }
    out["multiline"] = read(FILES / "multiline.pcsf")
    out["with_record"] = read(FILES / "grid2d_with_record.pcsf")
    try:
        out["mare2dem_tiny"] = open_source(
            datasets.path("mare2dem_tiny")
        ).model
    except ImportError:
        pass
    return out


MODELS = _models()


# ------------------------------------------------------------- sources
@pytest.mark.parametrize(
    "name, kind",
    [("occam2d_tiny", "occam2d"), ("modem_tiny", "modem")],
)
def test_open_run_folder(name, kind):
    loaded = open_source(datasets.path(name))
    assert loaded.kind == kind
    assert loaded.files
    assert loaded.title.endswith(f"({kind})")


def test_open_native_file_and_pcsf_files(tmp_path):
    rho = datasets.path("modem_tiny") / "tiny_NLCG_002.rho"
    loaded = open_source(rho)
    assert loaded.kind == "modem"
    # tiny.dat next to the model gives the stations
    assert len(loaded.model.stations.name) == 2
    # the station Z convention is guessed, which is reported
    assert any("Z column" in w for w in loaded.warnings)
    for suffix, kind in (
        (".pcsf", "pcsf"),
        (".pcsm", "pcsm"),
        (".pcsm.gz", "pcsm"),
    ):
        path = write(loaded.model, tmp_path / f"m{suffix}")
        again = open_source(path)
        assert again.kind == kind
        np.testing.assert_array_equal(
            again.model.resistivity, loaded.model.resistivity
        )


def test_open_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        open_source(tmp_path / "missing.pcsf")
    other = tmp_path / "notes.txt"
    other.write_text("x")
    with pytest.raises(FormatError, match="not a PCSF"):
        open_source(other)
    with pytest.raises(FormatError, match="no Occam2D"):
        open_source(tmp_path)


def test_latest_iteration_is_read(tmp_path):
    src = datasets.path("modem_tiny")
    for f in src.iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())
    # an earlier iteration with another value must not be chosen
    text = (src / "tiny_NLCG_002.rho").read_text()
    (tmp_path / "tiny_NLCG_001.rho").write_text(text)
    loaded = open_source(tmp_path)
    assert loaded.files[0].name == "tiny_NLCG_002.rho"


# ------------------------------------------------------------- figures
@pytest.mark.parametrize("name", sorted(MODELS))
def test_every_view_draws(name):
    model = MODELS[name]
    for view in figures.views(model):
        n = figures.n_positions(model, view)
        assert n >= 1
        for index in {0, n - 1}:
            ax = figures.draw(
                Figure(), model, view, index, fit=True, max_depth=100.0
            )
            assert ax.get_title().startswith(view)


def test_views_and_positions():
    m = MODELS["modem_tiny"]
    nz, ny, nx = m.resistivity.shape
    assert figures.n_positions(m, "depth slice") == nz
    assert figures.n_positions(m, "y section") == ny
    assert figures.n_positions(m, "x section") == nx
    with pytest.raises(ValueError, match="not available"):
        figures.n_positions(m, "mesh")
    ml = MODELS["multiline"]
    assert figures.n_positions(ml, "line") == len(ml.geometry.lines)


def test_grid3d_drawn_in_station_frame():
    m = MODELS["modem_tiny"]
    ax = figures.draw(Figure(), m, "depth slice", 0)
    g = m.geometry
    x0 = g.x_nodes[0] + g.origin[0]
    assert ax.get_xlim()[0] == pytest.approx(x0)
    lab = figures.position_label(m, "x section", 0)
    assert lab == f"x = {g.x[0] + g.origin[0]:.6g} m"


def test_color_range_ignores_air():
    m = MODELS["occam2d_tiny"]
    lo, _ = figures.color_range(m)
    air = m.resistivity.copy()
    air[0, :] = 1e12
    m2 = type(m)(geometry=m.geometry, resistivity=air)
    lo2, hi2 = figures.color_range(m2)
    assert hi2 < 8.0
    assert lo2 >= lo - 1e-12


def test_color_range_constant_model():
    m = MODELS["occam2d_tiny"]
    flat = type(m)(
        geometry=m.geometry,
        resistivity=np.full(m.resistivity.shape, 100.0),
    )
    assert figures.color_range(flat) == pytest.approx((1.5, 2.5))


def test_depth_limit_and_fit():
    m = MODELS["modem_tiny"]
    ax = figures.draw(
        Figure(), m, "y section", 0, max_depth=15.0, fit=True
    )
    assert max(ax.get_ylim()) == pytest.approx(15.0)
    st = m.stations
    span = max(st.x) - min(st.x)
    lo, hi = ax.get_xlim()
    pad = max(0.2 * span, 100.0)
    assert (lo, hi) == pytest.approx(
        (min(st.x) - pad, max(st.x) + pad)
    )


# ------------------------------------------------------------- summary
@pytest.mark.parametrize("name", sorted(MODELS))
def test_summary_tables(name, tmp_path):
    m = MODELS[name]
    rows = dict(summary.summary_rows(m, "src"))
    assert rows["Source"] == "src"
    assert rows["Geometry"] == m.kind
    header, srows = summary.station_rows(m)
    assert header[0] == "name"
    n = 0 if m.stations is None else len(m.stations.name)
    assert len(srows) == n
    conf = summary.conformance_rows(m)
    assert conf and all(len(r) == 3 for r in conf)
    header, table = summary.cell_table(m)
    assert header[-1] == "rho_ohm_m"
    assert table.shape[1] == len(header)
    path = summary.write_csv(tmp_path / "c.csv", header, table)
    lines = path.read_text().splitlines()
    assert len(lines) == table.shape[0] + 1


def test_cell_table_values():
    m = MODELS["modem_tiny"]
    header, table = summary.cell_table(m)
    assert header == ["x", "y", "z", "rho_ohm_m"]
    np.testing.assert_array_equal(table[:, 3], m.resistivity.ravel())
    _, ny, nx = m.resistivity.shape
    k, j, i = 1, 2, 3
    row = table[(k * ny + j) * nx + i]
    g = m.geometry
    assert tuple(row[:3]) == (g.x[i], g.y[j], g.z[k])


def test_record_rows():
    rows, req, _ = summary.record_rows(MODELS["with_record"])
    assert rows and req == []
    fields = dict(rows)
    assert "solver" in fields
    rows, req, _ = summary.record_rows(MODELS["occam2d_tiny"])
    assert rows == [] and "solver" in req


def test_metadata_tree_is_plain():
    tree = summary.metadata_tree(MODELS["modem_tiny"])
    assert "history" in tree

    def walk(v):
        if isinstance(v, dict):
            for sub in v.values():
                walk(sub)
        else:
            assert not isinstance(v, np.ndarray)

    walk(tree)


# ---------------------------------------------------------- statistics
def test_view_values_match_views():
    m = MODELS["modem_tiny"]
    nz, ny, nx = m.resistivity.shape
    assert figures.view_values(m, "depth slice", 1).size == ny * nx
    assert figures.view_values(m, "y section", 0).size == nz * nx
    assert figures.view_values(m, "x section", 0).size == nz * ny
    np.testing.assert_array_equal(
        figures.view_values(m, "depth slice", 1),
        m.resistivity[1].ravel(),
    )
    ml = MODELS["multiline"]
    line = ml.geometry.lines[-1]
    np.testing.assert_array_equal(
        figures.view_values(ml, "line", 99),
        np.ravel(line.resistivity),
    )


def test_value_stats():
    s = summary.value_stats([10.0, 100.0, 1000.0, np.nan, -1.0, 1e12])
    assert (s["n"], s["n_missing"], s["n_air"], s["n_earth"]) == (
        6,
        2,
        1,
        3,
    )
    assert s["median"] == pytest.approx(100.0)
    assert s["min"] == 10.0 and s["max"] == 1000.0
    assert s["log10_mean"] == pytest.approx(2.0)
    assert s["log10_std"] == pytest.approx(np.sqrt(2.0 / 3.0))
    empty = summary.value_stats([np.nan, 1e13])
    assert empty["n_earth"] == 0 and empty["median"] is None
