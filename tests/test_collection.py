"""The doctests of Qt modules are skipped where PySide6 is missing."""

import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "src" / "pcsf" / "studio"


def _conftest():
    spec = importlib.util.spec_from_file_location(
        "root_conftest", ROOT / "conftest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _imports_qt_at_top(path):
    """True when the module imports PySide6 outside any function."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (
            node.module or ""
        ).startswith("PySide6"):
            return True
        if isinstance(node, ast.Import) and any(
            a.name.startswith("PySide6") for a in node.names
        ):
            return True
    return False


def test_every_qt_module_is_skipped_without_pyside6():
    # A Studio module that imports PySide6 at module level fails the
    # doctest collection of the core-only CI jobs unless the root
    # conftest skips it (regression: convert_page.py).
    qt = {
        p.name for p in STUDIO.glob("*.py") if _imports_qt_at_top(p)
    }
    assert qt, "no Qt module found; the check is wrong"
    assert qt == set(_conftest()._QT_MODULES)
