"""Tests for the pcsf command-line tool."""

import json

import numpy as np

import pcsf
from pcsf.cli.main import main


def _write(tmp_path):
    native = np.array([[1.0, 2.0], [3.0, 4.0]])
    m = pcsf.PCSFModel(geometry=pcsf.Grid2DGeometry(x=[0.0, 1.0], z=[1.0, 2.0]),
                       resistivity=10.0 ** native, resistivity_native=native,
                       resistivity_native_encoding="log10")
    return pcsf.write(m, tmp_path / "m.pcsf")


def test_cli_info_validate_convert_compare(tmp_path, capsys):
    p = _write(tmp_path)
    assert main(["info", str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "grid2d"
    assert main(["validate", str(p)]) == 0
    q = tmp_path / "m.pcsm"
    assert main(["convert", str(p), str(q)]) == 0
    assert main(["compare", str(p), str(q)]) == 0
    out = capsys.readouterr().out
    assert '"rms": 0.0' in out
    assert main(["version"]) == 0


def test_cli_read_error_exit_code(tmp_path):
    bad = tmp_path / "bad.pcsf"
    bad.write_bytes(b"nope")
    assert main(["info", str(bad)]) == 2
