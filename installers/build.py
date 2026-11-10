"""Build and check the PCSF Studio bundle, then package it.

Steps:

1. Freeze PCSF Studio with PyInstaller into ``dist/pcsf-studio/``
   (``installers/pyinstaller/pcsf-studio.spec``).
2. Run the frozen executable with ``--self-test --report``: every
   bundled dataset is opened, drawn and converted. A bundle that
   misses a module or a data file fails here, not on a user's
   machine.
3. Package, when the platform tool is available:
   Windows, Inno Setup (``ISCC``) ->
   ``dist/pcsf-studio-<v>-setup.exe``;
   Linux, ``appimagetool`` -> ``dist/pcsf-studio-<v>-x86_64.AppImage``
   and ``makeself`` -> ``dist/pcsf-studio-<v>-linux.sh``.
   Without the tool, the step is reported as skipped.

Run from the repository root, in an environment with
``pip install -e ".[studio,emc,mare2dem]" pyinstaller``::

    python installers/build.py [--skip-freeze] [--no-package]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUNDLE = DIST / "pcsf-studio"
HERE = ROOT / "installers"


def version() -> str:
    sys.path.insert(0, str(ROOT / "src"))
    from pcsf._version import __version__

    return __version__


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def clean_path() -> str:
    """PATH without the directories of other Python installations.

    PyInstaller resolves DLL dependencies through PATH, so a base
    conda installation on PATH can lend the bundle its own copies
    (for example ICU 58 as ``icuuc.dll``, which then shadows the
    Windows ICU that Qt 6 needs). Directories inside the build
    environment and outside any Python installation are kept, after
    the build environment's own DLL folders.
    """
    prefix = Path(sys.prefix).resolve()
    keep = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        p = Path(entry)
        try:
            p = p.resolve()
        except OSError:
            continue
        inside = prefix == p or prefix in p.parents
        foreign = any(
            (q / "python.exe").exists() or (q / "conda-meta").exists()
            for q in (p, *p.parents)
        )
        if inside or not foreign:
            keep.append(entry)
    # The build environment's own DLL folders come first, as after
    # ``conda activate`` (a conda Python finds e.g. libffi there).
    own = [
        prefix / sub
        for sub in (
            "",
            "Library/mingw-w64/bin",
            "Library/usr/bin",
            "Library/bin",
            "Scripts",
            "bin",
        )
    ]
    first = [str(d) for d in own if d.is_dir()]
    return os.pathsep.join(first + keep)


def freeze() -> None:
    env = dict(os.environ, PATH=clean_path())
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--distpath",
            str(DIST),
            "--workpath",
            str(ROOT / "build" / "pyinstaller"),
            str(HERE / "pyinstaller" / "pcsf-studio.spec"),
        ],
        env=env,
    )


def executable() -> Path:
    name = "pcsf-studio.exe" if os.name == "nt" else "pcsf-studio"
    return BUNDLE / name


def self_test() -> None:
    exe = executable()
    if not exe.exists():
        raise SystemExit(
            f"no bundle at {exe}; run without --skip-freeze first"
        )
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "report.txt"
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        proc = subprocess.run(
            [str(exe), "--self-test", "--report", str(report)],
            env=env,
            timeout=600,
        )
        text = report.read_text() if report.exists() else "(no report)"
    print(text)
    if proc.returncode != 0 or "self-test passed" not in text:
        raise SystemExit("frozen self-test failed")


def _tool(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for base in (
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("ProgramFiles"),
    ):
        if base:
            cand = Path(base) / "Inno Setup 6" / "ISCC.exe"
            if "ISCC" in names and cand.exists():
                return str(cand)
    return None


def package_windows(v: str) -> None:
    iscc = _tool("ISCC", "iscc")
    if iscc is None:
        print("skip: Inno Setup (ISCC) not found")
        return
    run(
        [
            iscc,
            f"/DMyAppVersion={v}",
            f"/DDistDir={BUNDLE}",
            f"/O{DIST}",
            str(HERE / "windows" / "pcsf-studio.iss"),
        ]
    )


def package_linux(v: str) -> None:
    script = HERE / "linux" / "package.sh"
    run(["bash", str(script), v, str(BUNDLE), str(DIST)])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--skip-freeze",
        action="store_true",
        help="reuse dist/pcsf-studio",
    )
    p.add_argument(
        "--no-package",
        action="store_true",
        help="stop after the self-test",
    )
    args = p.parse_args(argv)
    v = version()
    if not args.skip_freeze:
        freeze()
    self_test()
    if args.no_package:
        return 0
    if sys.platform == "win32":
        package_windows(v)
    elif sys.platform.startswith("linux"):
        package_linux(v)
    else:
        print(f"skip: no packaging step for {sys.platform}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
