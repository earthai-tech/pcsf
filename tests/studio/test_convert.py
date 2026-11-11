"""Tests of the conversion used by the Convert page (no Qt)."""

import numpy as np
import pytest

from pcsf import datasets, read
from pcsf.exceptions import FormatError
from pcsf.studio.convert import (
    FORMATS,
    convert_source,
    default_stem,
    output_paths,
)
from pcsf.studio.sources import SOURCE_KINDS, source_kind


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("occam2d_tiny", "occam2d"),
        ("modem_tiny", "modem"),
        ("mare2dem_tiny", "mare2dem"),
    ],
)
def test_source_kind_of_run_folders(name, kind):
    assert source_kind(datasets.path(name)) == kind
    assert kind in SOURCE_KINDS


def test_source_kind_of_files(tmp_path):
    for suffix, kind in (
        (".pcsf", "pcsf"),
        (".pcsm", "pcsm"),
        (".pcsm.gz", "pcsm"),
        (".nc", "emc"),
        (".rho", "modem"),
        (".3.resistivity", "mare2dem"),
    ):
        path = tmp_path / f"m{suffix}"
        path.write_bytes(b"")
        assert source_kind(path) == kind, suffix
    other = tmp_path / "notes.txt"
    other.write_text("x")
    assert source_kind(other) is None
    assert source_kind(tmp_path / "missing.pcsf") is None
    assert source_kind(tmp_path / "empty_dir_absent") is None
    (tmp_path / "empty").mkdir()
    assert source_kind(tmp_path / "empty") is None


def test_default_stem_and_outputs(tmp_path):
    assert default_stem("m_NLCG_100.rho") == "m_NLCG_100"
    assert default_stem("demo.6.resistivity") == "demo.6"
    assert default_stem("a.PCSM.GZ") == "a"
    assert default_stem(tmp_path) == tmp_path.name
    paths = output_paths(
        tmp_path / "run" / "m.rho", ["pcsm", "pcsf", "pcsm"]
    )
    assert [p.name for p in paths] == ["m.pcsm", "m.pcsf"]
    assert paths[0].parent == tmp_path / "run"
    with pytest.raises(ValueError, match="at least one"):
        output_paths("m.rho", [])
    with pytest.raises(ValueError, match="unknown format"):
        output_paths("m.rho", ["vtk"])


@pytest.mark.parametrize("name", ["occam2d_tiny", "modem_tiny"])
def test_convert_every_format(tmp_path, name):
    res = convert_source(
        datasets.path(name), list(FORMATS), out_dir=tmp_path
    )
    assert [p.suffixes[-1] for p in res.outputs] == [
        ".pcsf",
        ".pcsm",
        ".gz",
    ]
    models = [read(p) for p in res.outputs]
    for m in models[1:]:
        assert m.kind == models[0].kind == res.model_kind
        # bit for bit, air (NaN) cells included
        assert np.array_equal(
            m.resistivity, models[0].resistivity, equal_nan=True
        )
    assert res.conformance is True and res.failures == []
    assert res.seconds >= 0


def test_convert_refuses_to_overwrite(tmp_path):
    src = datasets.path("occam2d_tiny")
    first = convert_source(src, out_dir=tmp_path)
    stamp = first.outputs[0].stat().st_mtime_ns
    with pytest.raises(FileExistsError, match="exists"):
        convert_source(src, out_dir=tmp_path)
    assert first.outputs[0].stat().st_mtime_ns == stamp
    again = convert_source(src, out_dir=tmp_path, overwrite=True)
    assert again.outputs == first.outputs


def test_reencode_and_guard_against_replacing_source(tmp_path):
    pcsf_file = convert_source(
        datasets.path("modem_tiny"), out_dir=tmp_path, stem="m"
    ).outputs[0]
    res = convert_source(pcsf_file, ["pcsm"], check=False)
    assert res.kind == "pcsf" and res.conformance is None
    assert res.outputs == [tmp_path / "m.pcsm"]
    with pytest.raises(ValueError, match="replace the source"):
        convert_source(pcsf_file, ["pcsf"], overwrite=True)


def test_unreadable_source_writes_nothing(tmp_path):
    bad = tmp_path / "bad.pcsm"
    bad.write_text("not a model")
    out = tmp_path / "out"
    with pytest.raises(FormatError):
        convert_source(bad, ["pcsf"], out_dir=out)
    assert not out.exists()
