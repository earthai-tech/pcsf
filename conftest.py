"""Test collection settings shared by tests/ and the doctests."""

import importlib.util

# PCSF Studio needs the optional studio dependencies: the widgets
# import PySide6 at module level and the figure doctests draw with
# matplotlib. Skip those doctests where they are not installed.
# Every Studio module that imports PySide6 at module level is listed.
_QT_MODULES = ("window.py", "convert_page.py")

collect_ignore_glob = []
if importlib.util.find_spec("PySide6") is None:
    collect_ignore_glob += [
        f"src/pcsf/studio/{name}" for name in _QT_MODULES
    ]
if importlib.util.find_spec("matplotlib") is None:
    collect_ignore_glob.append("src/pcsf/studio/figures.py")
