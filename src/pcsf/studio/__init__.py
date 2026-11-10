"""PCSF Studio, the graphical viewer and inspector of PCSF models.

PCSF Studio opens ``.pcsf`` and ``.pcsm`` files, native solver
results (Occam2D, ModEM, MARE2DEM) and EMC netCDF files, draws their
sections, depth slices and meshes, and lists their stations,
metadata, inversion record and conformance. It converts between PCSF
and PCSM and exports figures and CSV tables. It does not edit
models.

Install with ``pip install "pcsf[studio]"`` and start with
``pcsf-studio``, ``pcsf studio`` or ``python -m pcsf.studio``.

The application is split in a part without Qt, usable and tested on
its own, and thin Qt widgets:

- :mod:`pcsf.studio.sources`: opening files and run folders;
- :mod:`pcsf.studio.figures`: matplotlib views;
- :mod:`pcsf.studio.summary`: inspector tables and CSV exports;
- :mod:`pcsf.studio.window`: :class:`ModelView` (embeddable) and
  :class:`StudioWindow` (needs PySide6).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from ..exceptions import MissingDependencyError

__all__ = ["ModelView", "StudioWindow", "main", "self_test"]

_QT_NAMES = ("ModelView", "StudioWindow")


def _require_qt() -> None:
    # PySide6 is imported here, before matplotlib's Qt backend, so
    # that matplotlib binds to it and a broken installation reports
    # its own error instead of matplotlib's "no Qt binding".
    try:
        import matplotlib  # noqa: F401
        import PySide6.QtCore
        import PySide6.QtGui
        import PySide6.QtWidgets  # noqa: F401
    except ImportError as exc:
        raise MissingDependencyError(
            exc.name or "PySide6",
            extra="studio",
            feature="PCSF Studio",
        ) from exc


def __getattr__(name: str) -> Any:
    if name in _QT_NAMES:
        _require_qt()
        from . import window

        return getattr(window, name)
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


def self_test(report: Any = None) -> int:
    """Open, draw and convert every bundled dataset without a window.

    Used to check an installed or frozen build: each dataset of
    :mod:`pcsf.datasets` is opened through the Studio, every view is
    drawn in a :class:`ModelView` with the light and the dark theme
    and saved as PNG, and the model is written as PCSM and read
    back.

    Parameters
    ----------
    report : path-like, optional
        File receiving one line per check, for builds without a
        console; lines are printed otherwise.

    Returns
    -------
    int
        0 when every check passed, 1 otherwise.
    """
    import os
    import tempfile
    import traceback
    from pathlib import Path

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _require_qt()
    from .. import datasets, read, write
    from . import figures
    from .sources import open_source
    from .style import DARK, LIGHT
    from .window import ModelView, application, logo_icon

    app = application()  # noqa: F841 (kept alive for the widgets)
    lines, failed = [], 0
    # The logo is an SVG: a build without Qt's SVG plugins draws an
    # empty icon, which a null check would not see.
    image = logo_icon().pixmap(32, 32).toImage()
    opaque = sum(
        image.pixelColor(x, y).alpha() > 0
        for x in range(0, 32, 4)
        for y in range(0, 32, 4)
    )
    if opaque:
        lines.append("ok   logo (SVG icon)")
    else:
        failed += 1
        lines.append("FAIL logo: the SVG icon renders empty")
    with tempfile.TemporaryDirectory() as tmp:
        for name in datasets.NAMES:
            try:
                loaded = open_source(datasets.path(name))
                view = ModelView()
                view.set_model(loaded)
                failures = []
                view.plot_failed.connect(failures.append)
                for theme in (LIGHT, DARK):
                    view.set_theme(theme)
                    for v in figures.views(loaded.model):
                        view.view_box.setCurrentText(v)
                        view.redraw()
                        view.save_figure(Path(tmp) / f"{name}_{v}.png")
                assert not failures, failures[0]
                back = read(
                    write(loaded.model, Path(tmp) / f"{name}.pcsm")
                )
                assert back.kind == loaded.model.kind
                lines.append(f"ok   {name} ({loaded.model.kind})")
            except Exception:
                failed += 1
                lines.append(f"FAIL {name}\n{traceback.format_exc()}")
    lines.append("self-test " + ("failed" if failed else "passed"))
    text = "\n".join(lines) + "\n"
    if report is not None:
        Path(report).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Start PCSF Studio.

    Parameters
    ----------
    argv : sequence of str, optional
        Command-line arguments, ``sys.argv[1:]`` by default:
        an optional file or run folder to open, ``--theme`` with
        ``system``, ``light`` or ``dark``, ``--self-test`` to
        run :func:`self_test` instead of opening a window, and
        ``--report PATH`` for its output.

    Returns
    -------
    int
        Exit status of the application.

    Raises
    ------
    MissingDependencyError
        If PySide6 or matplotlib is not installed.
    """
    p = argparse.ArgumentParser(
        prog="pcsf-studio",
        description="PCSF Studio: view and inspect PCSF models",
    )
    p.add_argument(
        "path", nargs="?", help="file or run folder to open"
    )
    p.add_argument(
        "--self-test",
        action="store_true",
        help="check the installation without a window",
    )
    p.add_argument("--report", help="write the self-test result here")
    p.add_argument(
        "--theme",
        choices=("system", "light", "dark"),
        help="theme to start with (default: the last one used)",
    )
    args = p.parse_args(argv)
    if args.self_test:
        return self_test(args.report)
    _require_qt()
    from .window import StudioWindow, application

    app = application()
    win = StudioWindow(args.path, theme=args.theme)
    # An error in a Qt slot would otherwise end a frozen build
    # without a word; the window reports it and keeps running.
    previous = sys.excepthook
    sys.excepthook = win.report_unexpected
    try:
        win.show()
        return int(app.exec())
    finally:
        sys.excepthook = previous
