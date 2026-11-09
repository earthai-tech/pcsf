"""Cross-checks with pyCSAMT, the original implementation.

Skipped when pyCSAMT or the paper files are not available. They check
that (1) pcsf reads every file of the Geophysics paper bit for bit like
pyCSAMT, (2) pyCSAMT reads files written by pcsf, and (3) the NumPy-only
sampling of pcsf reproduces pyCSAMT's SciPy/Matplotlib sampling.
"""

from pathlib import Path

import numpy as np
import pytest

import pcsf
import pcsf.algorithms

PAPER_DATA = Path(r"D:/projects/pycsamt/PAPERS/GEOPHYSICS/data")
pyformat = pytest.importorskip("pycsamt.format")
FILES = sorted(PAPER_DATA.glob("*.pcsf")) if PAPER_DATA.exists() else []
pytestmark = pytest.mark.skipif(not FILES, reason="paper data not available")


def _arrays(model):
    if model.kind == "multiline":
        return [np.asarray(ln.resistivity) for ln in model.geometry.lines]
    return [np.asarray(model.resistivity)]


@pytest.mark.parametrize("path", FILES, ids=[p.stem for p in FILES])
def test_reads_paper_files_like_pycsamt(path):
    ours, theirs = pcsf.read(path), pyformat.read_pcsf(path)
    for a, b in zip(_arrays(ours), _arrays(theirs)):
        assert np.array_equal(a, b, equal_nan=True)
    assert ours.metadata == theirs.metadata
    assert pcsf.validate(ours).passed, str(pcsf.validate(ours))


@pytest.mark.parametrize("path", FILES, ids=[p.stem for p in FILES])
def test_pycsamt_reads_pcsf_output(path, tmp_path):
    out = pcsf.write(pcsf.read(path), tmp_path / "x.pcsf")
    for a, b in zip(_arrays(pyformat.read_pcsf(out)), _arrays(pyformat.read_pcsf(path))):
        assert np.array_equal(a, b, equal_nan=True)


@pytest.mark.parametrize("stem", ["baohuashan_modem3d", "baohuashan_occam2d_L18", "mare2dem_demo"])
def test_sampling_matches_pycsamt(stem):
    path = PAPER_DATA / f"{stem}.pcsf"
    m_ours, m_theirs = pcsf.read(path), pyformat.read_pcsf(path)
    rng = np.random.default_rng(3)
    g = m_ours.geometry
    if m_ours.kind == "grid3d":
        pts = np.column_stack([rng.uniform(g.x.min(), g.x.max(), 3000),
                               rng.uniform(g.y.min(), g.y.max(), 3000),
                               rng.uniform(g.z.min(), g.z.max(), 3000)])
    elif m_ours.kind == "grid2d":
        pts = np.column_stack([rng.uniform(g.x.min(), g.x.max(), 3000),
                               rng.uniform(g.z.min(), g.z.max(), 3000)])
    else:
        n = np.asarray(g.nodes)
        pts = np.column_stack([rng.uniform(-5e3, 3e4, 3000), rng.uniform(0, 1.5e4, 3000)])
    ours = pcsf.algorithms.sample_log10(m_ours, pts)
    theirs = pyformat.sample_log10(m_theirs, pts)
    both = np.isfinite(ours) & np.isfinite(theirs)
    assert np.array_equal(np.isfinite(ours), np.isfinite(theirs))
    np.testing.assert_allclose(ours[both], theirs[both], rtol=0, atol=1e-10)
