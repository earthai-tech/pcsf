"""Reference runner of the PCSF conformance suite.

Reads every file listed in ``expected.json`` with pcsf and checks the
outcome. Other implementations reproduce the same checks with their
own reader; the expectations are plain JSON.

Usage::

    python conformance/run.py [folder]

The exit status is 0 when every case passes and 1 otherwise.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

import pcsf

HERE = Path(__file__).resolve().parent


def _digest(model: pcsf.PCSFModel) -> str | None:
    if model.resistivity is None:
        return None
    arr = np.ascontiguousarray(model.resistivity, dtype="<f8")
    return hashlib.sha256(arr.tobytes()).hexdigest()


def run(folder: Path = HERE) -> list[tuple[str, bool, str]]:
    """Check every case of the suite.

    Parameters
    ----------
    folder : pathlib.Path
        Folder holding ``expected.json`` and ``files/``.

    Returns
    -------
    list of tuple
        ``(file, passed, detail)`` per case.
    """
    spec = json.loads((folder / "expected.json").read_text("utf-8"))
    files = folder / "files"
    out: list[tuple[str, bool, str]] = []
    for case in spec["valid"]:
        try:
            model = pcsf.read(files / case["file"])
            report = pcsf.validate(model)
        except pcsf.PCSFError as exc:
            out.append((case["file"], False, f"read failed: {exc}"))
            continue
        problems = []
        if model.kind != case["kind"]:
            problems.append(f"kind {model.kind}")
        if _digest(model) != case["resistivity_sha256"]:
            problems.append("resistivity differs")
        if not report.passed:
            failed = [r.rule for r in report.failures]
            problems.append(f"rules failed: {failed}")
        out.append((case["file"], not problems, "; ".join(problems)))
    for case in spec["rule"]:
        try:
            report = pcsf.validate(pcsf.read(files / case["file"]))
        except pcsf.PCSFError as exc:
            out.append((case["file"], False, f"read failed: {exc}"))
            continue
        failed = sorted({r.rule for r in report.failures})
        ok = failed == sorted(case["failed_rules"])
        out.append((case["file"], ok, f"failed rules {failed}"))
    for case in spec["reject"]:
        try:
            pcsf.read(files / case["file"])
        except pcsf.PCSFError as exc:
            name = type(exc).__name__
            out.append((case["file"], name == case["error"], name))
        else:
            out.append((case["file"], False, "accepted"))
    return out


def main(argv: list[str]) -> int:
    folder = Path(argv[1]) if len(argv) > 1 else HERE
    results = run(folder)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:36s} {detail}")
    n_ok = sum(ok for _, ok, _ in results)
    print(f"{n_ok}/{len(results)} cases passed")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
