"""Run the conformance suite in ``conformance/`` as tests."""

import json
import runpy
from pathlib import Path

import pytest

SUITE = Path(__file__).resolve().parents[1] / "conformance"
RUN = runpy.run_path(str(SUITE / "run.py"))["run"]
RESULTS = RUN(SUITE)


def test_suite_lists_every_file():
    spec = json.loads((SUITE / "expected.json").read_text("utf-8"))
    listed = {
        case["file"]
        for group in ("valid", "rule", "reject")
        for case in spec[group]
    }
    on_disk = {p.name for p in (SUITE / "files").iterdir()}
    assert listed == on_disk


@pytest.mark.parametrize(
    ("name", "ok", "detail"), RESULTS, ids=[r[0] for r in RESULTS]
)
def test_case(name, ok, detail):
    assert ok, f"{name}: {detail}"
