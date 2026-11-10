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


def test_statistics_panel_follows_view(app):
    view = ModelView()
    view.set_model(open_source(datasets.path("modem_tiny")))
    from pcsf.studio.summary import value_stats

    tiles = view.stats.model_block.tiles
    # the tile counts earth cells, without air and missing values
    n = value_stats(view.loaded.model.resistivity)["n_earth"]
    assert tiles["cells"].value.text().replace(",", "") == str(n)
    view.view_box.setCurrentText("depth slice")
    view.slider.setValue(0)
    layer = view.loaded.model.resistivity[0]
    view_tiles = view.stats.view_block.tiles
    expected = value_stats(layer)["n_earth"]
    assert view_tiles["cells"].value.text() == str(expected)
    assert "depth slice" in view.stats.view_title.text()


def test_header_chips(app):
    view = ModelView()
    view.set_model(open_source(datasets.path("occam2d_tiny")))
    chips = [
        view.chips.itemAt(i).widget().text()
        for i in range(view.chips.count())
        if view.chips.itemAt(i).widget() is not None
    ]
    assert chips[0] == "grid2d"
    assert any(c.startswith("conformance ") for c in chips)
    # reopening replaces the chips instead of adding to them
    view.set_model(open_source(datasets.path("modem_tiny")))
    widgets = [
        view.chips.itemAt(i).widget()
        for i in range(view.chips.count())
    ]
    assert sum(w is not None for w in widgets) == len(
        [w for w in widgets if w is not None]
    )
    assert widgets[0].text() == "grid3d"


def test_welcome_recent_and_help(app, tmp_path):
    from PySide6.QtCore import QSettings

    settings = QSettings(
        str(tmp_path / "studio.ini"), QSettings.Format.IniFormat
    )
    win = StudioWindow(settings=settings)
    assert win.pages.currentWidget() is win.welcome
    model = tmp_path / "m.pcsf"
    __import__("pcsf").write(
        open_source(datasets.path("occam2d_tiny")).model, model
    )
    assert win.open(model)
    assert win.pages.currentWidget() is win.view
    assert settings.value("recent")[0] == str(model)
    # bundled samples are not added to the recent files
    assert win.open(datasets.path("modem_tiny"))
    assert len(win._recent()) == 1
    win.show_welcome()
    assert win.welcome.recent.count() == 1
    texts = [a.text() for a in win.help_menu.actions()]
    assert "About PCSF Studio" in texts
    assert not win.help_button.icon().isNull()


def test_logo_renders(app):
    from pcsf.studio.window import ICON_SVG, logo_icon

    assert ICON_SVG.exists()
    pixmap = logo_icon().pixmap(32, 32)
    assert not pixmap.isNull() and pixmap.width() == 32
