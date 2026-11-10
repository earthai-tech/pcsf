"""Build the PCSF conformance suite in ``conformance/``.

Three groups of cases are written, each listed in
``conformance/expected.json`` with the outcome a conforming reader
must produce:

``valid``
    Files of every geometry kind in both encodings. A reader must
    read them, pass every rule, and reproduce the canonical
    resistivity bit for bit (SHA-256 of the float64 C-order bytes).
``rule``
    Readable files that break exactly one rule (C2, C5, C7, C10). A
    reader
    must read them and report that rule as failed.
``reject``
    PCSM files altered so that a reader must refuse them, with the
    error class to raise (encoding, geometry, version, syntax).

Run from the repository root::

    python tools/make_conformance_suite.py
"""

from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import numpy as np

import pcsf
from pcsf.adapters import (
    mare2dem_to_pcsf,
    modem_to_pcsf,
    occam2d_to_pcsf,
)
from pcsf.core.record import InversionRecord, attach_inversion_record
from pcsf.core.schema import (
    DerivedVolume,
    Grid2DGeometry,
    Grid3DGeometry,
    LineEntry,
    MultilineGeometry,
    UnstructuredMeshGeometry,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "conformance"
CASES = OUT / "files"
STAMP = "2026-01-01T00:00:00+00:00"
CREATED_BY = "pcsf conformance suite"


def _digest(model: pcsf.PCSFModel) -> str | None:
    if model.resistivity is None:
        return None
    arr = np.ascontiguousarray(model.resistivity, dtype="<f8")
    return hashlib.sha256(arr.tobytes()).hexdigest()


def _stamp(model: pcsf.PCSFModel) -> pcsf.PCSFModel:
    model.created_at = STAMP
    model.created_by = CREATED_BY
    model.metadata = {
        k: v for k, v in model.metadata.items() if k != "workdir"
    }
    return model


def _models() -> dict[str, pcsf.PCSFModel]:
    d = pcsf.datasets.path
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        modem = modem_to_pcsf(
            d("modem_tiny") / "tiny_NLCG_002.rho",
            data=d("modem_tiny") / "tiny.dat",
            log=d("modem_tiny") / "tiny_NLCG.log",
        )
    m2d = d("mare2dem_tiny")
    tri = np.loadtxt(m2d / "tiny.ele.txt", dtype=int)
    mesh = mare2dem_to_pcsf(
        m2d / "tiny.1.resistivity",
        mesh=(
            np.loadtxt(m2d / "tiny.node.txt"),
            tri[:, :3],
            tri[:, 3],
        ),
        log=m2d / "tiny.logfile",
    )
    occam = occam2d_to_pcsf(
        d("occam2d_tiny"),
        station_lonlat={
            "S01": (117.0, 25.0),
            "S02": (117.001, 25.0),
            "S03": (117.002, 25.0),
        },
        station_elevations={"S01": 300.0, "S02": 305.0, "S03": 302.0},
    )
    geo = Grid2DGeometry(x=[0.0, 50.0, 100.0], z=[5.0, 15.0])
    rho = np.array([[10.0, 100.0, 1000.0], [20.0, 200.0, 2000.0]])
    lines = [
        LineEntry(f"L{i}", geo, rho * (i + 1), 200.0 * i, "real")
        for i in range(2)
    ]
    grid = Grid3DGeometry(
        x=[0.0, 50.0, 100.0], y=[0.0, 200.0], z=[5.0, 15.0]
    )
    volume = DerivedVolume(
        grid,
        np.stack([lines[0].resistivity, lines[1].resistivity], axis=1),
        derived_from=["L0", "L1"],
    )
    multiline = pcsf.PCSFModel(
        geometry=MultilineGeometry(lines, volume),
        source_backend="generic",
    )
    recorded = occam2d_to_pcsf(d("occam2d_tiny"))
    attach_inversion_record(
        recorded,
        InversionRecord(
            "Occam2D",
            solver_version="3.0",
            data={
                "components": ["TE rho", "TE phase"],
                "frequency_range_hz": [1.0, 1000.0],
                "n_stations": 3,
                "errors": "10 % on rho, 2.9 degrees on phase",
            },
            regularization={"type": "smoothness (Occam)"},
            misfit={
                "final_rms": 1.5,
                "termination": "iteration_limit",
            },
        ),
    )
    return {
        "grid2d_occam2d": occam,
        "grid3d_modem": modem,
        "mesh_mare2dem": mesh,
        "multiline": multiline,
        "grid2d_with_record": recorded,
    }


def _rule_cases() -> dict[str, tuple[pcsf.PCSFModel, str]]:
    geo = Grid2DGeometry(x=[0.0, 10.0], z=[5.0])
    negative = pcsf.PCSFModel(geometry=geo, resistivity=[[10.0, -5.0]])
    mismatch = pcsf.PCSFModel(
        geometry=geo,
        resistivity=[[10.0, 100.0]],
        resistivity_native=[[1.0, 3.0]],
        resistivity_native_encoding="log10",
    )
    grid = Grid3DGeometry(x=[0.0, 10.0], y=[0.0, 100.0], z=[5.0])
    lines = [
        LineEntry(f"L{i}", geo, [[10.0, 100.0]], 100.0 * i)
        for i in range(2)
    ]
    unlabelled = pcsf.PCSFModel(
        geometry=MultilineGeometry(
            lines,
            DerivedVolume(
                grid, np.full((1, 2, 2), 50.0), synthesized=False
            ),
        )
    )
    # Region ids numbered from 1, as MARE2DEM does, instead of the
    # 0-based indices PCSF requires.
    one_based = pcsf.PCSFModel(
        geometry=UnstructuredMeshGeometry(
            nodes=[[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
            connectivity=[[0, 1, 2], [1, 3, 2]],
            region_ids=[1, 2],
        ),
        resistivity=[10.0, 100.0],
        resistivity_by_region=[10.0, 100.0],
    )
    return {
        "rule_c2_negative": (negative, "C2.positive"),
        "rule_c5_native_mismatch": (mismatch, "C5.native"),
        "rule_c7_not_synthesized": (unlabelled, "C7.synthesized"),
        "rule_c10_region_base": (one_based, "C10.regions"),
    }


def _base_pcsm() -> str:
    model = pcsf.PCSFModel(
        geometry=Grid2DGeometry(x=[0.0, 10.0], z=[5.0]),
        resistivity=[[10.0, 100.0]],
        resistivity_native=np.log10([[10.0, 100.0]]),
        resistivity_native_encoding="log10",
        stations=pcsf.StationTable(
            name=["A", "B"],
            x=[0.0, 10.0],
            y=[0.0, 0.0],
            z=[1.0, 2.0],
            lon=[117.0, 117.001],
            lat=[25.0, 25.0],
        ),
        created_at=STAMP,
        created_by=CREATED_BY,
    )
    path = CASES / "_base.pcsm"
    pcsf.write(model, path)
    text = path.read_text(encoding="utf-8")
    path.unlink()
    return text


def _reject_cases(base: str) -> dict[str, tuple[str, str]]:
    return {
        "reject_unknown_encoding": (
            base.replace(
                "RESISTIVITY_NATIVE_ENCODING log10",
                "RESISTIVITY_NATIVE_ENCODING log7",
            ),
            "EncodingError",
        ),
        "reject_shape_mismatch": (
            base.replace("NX 2", "NX 3").replace(
                " 0.0 10.0\nEND_X_COORDS",
                " 0.0 10.0 20.0\nEND_X_COORDS",
            ),
            "GeometryError",
        ),
        "reject_major_version": (
            base.replace("PCSM_VERSION 0.1.0", "PCSM_VERSION 9.0.0"),
            "VersionError",
        ),
        "reject_missing_block_end": (
            base.replace("END_RESISTIVITY\n", "", 1),
            "PCSMSyntaxError",
        ),
    }


def main() -> None:
    CASES.mkdir(parents=True, exist_ok=True)
    for old in CASES.iterdir():
        old.unlink()
    expected: dict[str, list[dict]] = {
        "format_version": pcsf.FORMAT_VERSION,
        "valid": [],
        "rule": [],
        "reject": [],
    }
    for name, model in _models().items():
        model = _stamp(model)
        report = pcsf.validate(model)
        assert report.passed, (name, str(report))
        for suffix in (".pcsf", ".pcsm", ".pcsm.gz"):
            path = CASES / f"{name}{suffix}"
            pcsf.write(model, path)
            back = pcsf.read(path)
            assert _digest(back) == _digest(model), (name, suffix)
            expected["valid"].append(
                {
                    "file": path.name,
                    "kind": model.kind,
                    "shape": None
                    if model.resistivity is None
                    else list(np.shape(model.resistivity)),
                    "resistivity_sha256": _digest(model),
                    "rules": sorted({r.rule for r in report.results}),
                }
            )
    for name, (model, rule) in _rule_cases().items():
        model = _stamp(model)
        report = pcsf.validate(model)
        assert [r.rule for r in report.failures] == [rule], name
        for suffix in (".pcsf", ".pcsm"):
            path = CASES / f"{name}{suffix}"
            pcsf.write(model, path)
            expected["rule"].append(
                {"file": path.name, "failed_rules": [rule]}
            )
    for name, (text, error) in _reject_cases(_base_pcsm()).items():
        path = CASES / f"{name}.pcsm"
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        try:
            pcsf.read(path)
        except pcsf.PCSFError as exc:
            assert type(exc).__name__ == error, (name, exc)
        else:
            raise AssertionError(f"{name} was not rejected")
        expected["reject"].append({"file": path.name, "error": error})
    with open(
        OUT / "expected.json", "w", encoding="utf-8", newline="\n"
    ) as fh:
        json.dump(expected, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    main()
