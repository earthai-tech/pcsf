"""Tests of the PCSF Studio widgets (need PySide6, run offscreen)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from pcsf import datasets, read
from pcsf.studio import main, self_test
from pcsf.studio.sources import open_source
from pcsf.studio.window import (
    ModelView,
    StudioWindow,
    application,
)


@pytest.fixture(scope="module")
def app():
    return application()


def test_model_view_tabs_and_views(app):
    view = ModelView()
    seen = []
    view.model_changed.connect(seen.append)
    loaded = open_source(datasets.path("modem_tiny"))
    view.set_model(loaded)
    assert seen == [loaded]
    tabs = [view.tabs.tabText(i) for i in range(view.tabs.count())]
    assert tabs[:5] == [
        "Summary",
        "Stations",
        "Metadata",
        "Record",
        "Conformance",
    ]
    # the guessed station Z convention is listed under Reading
    assert "Reading" in tabs
    items = [
        view.view_box.itemText(i) for i in range(view.view_box.count())
    ]
    assert items == ["depth slice", "x section", "y section"]
    for item in items:
        view.view_box.setCurrentText(item)
        assert view.slider.maximum() >= 0
        assert view.position.text()
    view.auto_range.setChecked(False)
    view.vmin.setValue(1.0)
    view.vmax.setValue(3.0)
    assert view.figure.axes[0].collections[0].get_clim() == (1.0, 3.0)


def test_window_open_save_and_errors(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    errors = []
    monkeypatch.setattr(
        QMessageBox, "critical", lambda *a, **k: errors.append(a)
    )
    win = StudioWindow()
    assert not any(a.isEnabled() for a in win._model_actions)
    assert not win.open(tmp_path / "missing.pcsf")
    assert errors
    assert win.open(datasets.path("occam2d_tiny"))
    assert all(a.isEnabled() for a in win._model_actions)
    assert "occam2d" in win.windowTitle()
    dst = tmp_path / "out.pcsm"
    win._run(
        lambda: __import__("pcsf").write(win.view.loaded.model, dst),
        dst,
    )
    assert read(dst).kind == "grid2d"
    assert str(dst) in win.statusBar().currentMessage()


def test_self_test_and_report(app, tmp_path):
    report = tmp_path / "report.txt"
    assert self_test(report) == 0
    text = report.read_text()
    assert "self-test passed" in text
    assert main(["--self-test", "--report", str(report)]) == 0
