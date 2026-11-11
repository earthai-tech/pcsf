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


@pytest.fixture
def settings(tmp_path):
    """Settings in a file; those of the user are left alone."""
    from PySide6.QtCore import QSettings

    return QSettings(
        str(tmp_path / "studio.ini"), QSettings.Format.IniFormat
    )


@pytest.fixture
def dialogs(monkeypatch):
    """Dialogs shown, as (title, text) pairs, without waiting."""
    from PySide6.QtWidgets import QMessageBox

    shown = []
    monkeypatch.setattr(
        QMessageBox,
        "exec",
        lambda box: shown.append((box.windowTitle(), box.text())),
    )
    return shown


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


def test_window_open_save_and_errors(app, tmp_path, settings, dialogs):
    win = StudioWindow(settings=settings)
    assert not any(a.isEnabled() for a in win._model_actions)
    assert not win.open(tmp_path / "missing.pcsf")
    assert dialogs == [("Cannot open", "missing.pcsf")]
    # nothing to open is not an error
    assert not win.open(None) and not win.open("")
    assert len(dialogs) == 1
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
    # a failed write is reported; a failed open keeps the model
    assert not win._run(lambda: 1 / 0, dst)
    assert dialogs[-1][0] == "Cannot write"
    bad = tmp_path / "bad.pcsm"
    bad.write_text("not a model")
    assert not win.open(bad)
    assert win.view.loaded.kind == "occam2d"
    assert win.view.title.text() == "occam2d_tiny"


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


def test_welcome_recent_and_help(app, tmp_path, settings):
    from PySide6.QtWidgets import QToolBar

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
    # help is a plain "?" at the right; the logo is at the left
    assert win.help_button.text() == "?"
    assert win.help_button.icon().isNull()
    assert not win.brand_button.icon().isNull()
    bar = win.findChild(QToolBar, "MainBar")
    order = [bar.widgetForAction(a) for a in bar.actions()]
    assert order[0] is win.brand_button
    assert order[-1] is win.help_button
    win.brand_button.click()
    assert win.pages.currentWidget() is win.welcome
    # the placeholder of an empty list opens nothing
    win.clear_recent()
    assert win._recent() == []
    win.welcome._activated(win.welcome.recent.item(0))
    assert win.pages.currentWidget() is win.welcome


def test_logo_renders(app):
    from pcsf.studio.window import ICON_SVG, logo_icon

    assert ICON_SVG.exists()
    pixmap = logo_icon().pixmap(32, 32)
    assert not pixmap.isNull() and pixmap.width() == 32


def _rgb(colour):
    return [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]


def test_themes(app, settings):
    from pcsf.studio.style import DARK, LIGHT, get_theme

    win = StudioWindow(settings=settings, theme="light")
    assert win.theme is LIGHT and win.view.theme is LIGHT
    win.open(datasets.path("modem_tiny"))
    win.set_theme("dark")
    assert win.theme is DARK
    assert settings.value("theme") == "dark"
    assert win.theme_actions["dark"].isChecked()
    assert DARK.panel in win.styleSheet()
    # the plot and the histogram take the colours of the theme
    fig = win.view.figure
    assert fig.get_facecolor()[:3] == pytest.approx(_rgb(DARK.panel))
    assert fig.axes[0].title.get_color() == DARK.ink
    hist = win.view.stats.hist_fig
    assert hist.get_facecolor()[:3] == pytest.approx(_rgb(DARK.panel))
    win.toggle_theme()
    assert win.theme is LIGHT
    # the choice is kept for the next window
    assert StudioWindow(settings=settings).theme_name == "light"
    with pytest.raises(ValueError, match="unknown theme"):
        win.set_theme("sepia")
    assert get_theme("system", system_dark=True) is DARK
    assert get_theme("SYSTEM") is LIGHT


def test_exported_figure_is_light(app, tmp_path):
    from matplotlib.image import imread

    from pcsf.studio.style import DARK

    view = ModelView()
    view.set_theme(DARK)
    view.set_model(open_source(datasets.path("occam2d_tiny")))
    dst = tmp_path / "fig.png"
    view.save_figure(dst, dpi=50)
    assert imread(dst)[0, 0, :3] == pytest.approx([1.0, 1.0, 1.0])
    # the figure on screen is dark again afterwards
    assert view.figure.axes[0].title.get_color() == DARK.ink


def test_window_fits_and_centres(app, settings):
    from pcsf.studio.window import DEFAULT_SIZE, SCREEN_SHARE

    win = StudioWindow(settings=settings)
    area = win.screen().availableGeometry()
    assert win.width() <= DEFAULT_SIZE[0]
    assert win.height() <= DEFAULT_SIZE[1]
    assert win.width() <= area.width() * SCREEN_SHARE
    assert win.height() <= area.height() * SCREEN_SHARE
    centre = win.geometry().center()
    assert abs(centre.x() - area.center().x()) <= 2
    assert abs(centre.y() - area.center().y()) <= 2
    default = (win.width(), win.height())
    # the next session opens at the default size again, centred,
    # but keeps the collapsed panels
    win.resize(default[0] - 100, default[1] - 100)
    win.stats_act.setChecked(False)
    win.close()
    assert settings.value("geometry") is None
    again = StudioWindow(settings=settings)
    assert (again.width(), again.height()) == default
    assert not again.stats_act.isChecked()
    assert again.view.stats.isHidden()
    assert again.inspector_act.isChecked()


def test_maximized_size_of_older_versions_is_ignored(app, settings):
    # earlier versions kept the geometry, maximized flag included;
    # the window opened full screen at every start (regression)
    win = StudioWindow(settings=settings)
    win.showMaximized()
    app.processEvents()
    settings.setValue("geometry", win.saveGeometry())
    win.close()
    again = StudioWindow(settings=settings)
    assert not again.isMaximized()
    area = again.screen().availableGeometry()
    assert again.width() < area.width()
    assert settings.value("geometry") is None


def test_statistics_collapse_to_the_right(app, settings):
    win = StudioWindow(settings=settings)
    win.open(datasets.path("modem_tiny"))
    win.show()
    app.processEvents()
    side = win.view.stats_side
    split = win.view.split
    plot_before = split.sizes()[1]
    seen = []
    side.toggled.connect(seen.append)
    side.set_expanded(False, animate=False)
    app.processEvents()
    assert win.view.stats.isHidden()
    assert side.width() <= side.edge.WIDTH + 4
    assert split.sizes()[1] > plot_before  # the plot got the room
    assert not win.stats_act.isChecked()  # the menu follows
    # the strip expands it again, at its former width
    side.edge.click()
    app.processEvents()
    assert side.expanded and win.stats_act.isChecked()
    assert seen == [False, True]
    for _ in range(50):  # let the slide finish
        app.processEvents()
        if side._anim is None:
            break
        side._anim.setCurrentTime(side.DURATION)
    assert not win.view.stats.isHidden()
    assert side.width() > 200
    # Ctrl+2 drives the same panel
    win.stats_act.setChecked(False)
    assert not side.expanded
    win.close()


def test_convert_page_converts_in_a_thread(app, tmp_path, settings):
    from pcsf import read

    win = StudioWindow(settings=settings)
    win.show_convert()
    page = win.convert
    assert win.pages.currentWidget() is page
    assert not page.convert_btn.isEnabled()  # empty list
    bad = tmp_path / "notes.txt"
    bad.write_text("not a model")
    added = page.add_sources(
        [
            datasets.path("occam2d_tiny"),
            datasets.path("modem_tiny"),
            datasets.path("occam2d_tiny"),  # duplicate
            bad,  # not recognised
        ]
    )
    assert added == 2 and page.table.rowCount() == 2
    assert "Skipped" in page.log.toPlainText()
    kinds = [page.table.item(r, 1).text() for r in range(2)]
    assert kinds == ["Occam2D run", "ModEM model"]
    page.format_boxes["pcsm.gz"].setChecked(True)
    page.into.setChecked(True)
    assert not page.convert_btn.isEnabled()  # no folder yet
    out = tmp_path / "out"
    page.folder_edit.setText(str(out))
    assert page.convert_btn.isEnabled()
    page.open_box.setChecked(True)
    done = []
    page.run_done.connect(done.append)
    assert page.start()
    assert page.busy and not page.convert_btn.isEnabled()
    assert page.wait()
    assert len(page.results) == 2 and done == [2]
    names = sorted(p.name for p in out.iterdir())
    assert len(names) == 4
    assert all(n.endswith((".pcsf", ".pcsm.gz")) for n in names)
    for path in out.iterdir():
        assert read(path).kind in ("grid2d", "grid3d")
    assert page.progress.value() == 2
    assert "Converted 2 source(s)" in page.log.toPlainText()
    # the first result is opened in the viewer
    assert win.pages.currentWidget() is win.view
    assert win.view.loaded.kind == "pcsf"
    # a second run without "replace" reports each source as failed
    win.show_convert()
    page.open_box.setChecked(False)
    assert page.start() and page.wait()
    log = page.log.toPlainText()
    assert log.count("FAIL") == 2 and "exists" in log
    states = [page.table.item(r, 2).text() for r in range(2)]
    assert states == ["failed", "failed"]
    # the choices come back in the next session
    win.close()
    again = StudioWindow(settings=settings)
    assert again.convert.formats() == ["pcsf", "pcsm.gz"]
    assert again.convert.out_dir() == out


def test_convert_page_drop_adds_sources(app, settings):
    win = StudioWindow(settings=settings)
    win.show_convert()

    class _Drop:
        def __init__(self, paths):
            from PySide6.QtCore import QMimeData, QUrl

            self.data = QMimeData()
            self.data.setUrls(
                [QUrl.fromLocalFile(str(p)) for p in paths]
            )

        def mimeData(self):
            return self.data

        def acceptProposedAction(self):
            pass

    win.dropEvent(_Drop([datasets.path("mare2dem_tiny")]))
    assert win.convert.table.rowCount() == 1
    assert win.pages.currentWidget() is win.convert


def test_panels_scroll_instead_of_clipping(app, settings):
    from PySide6.QtWidgets import QScrollArea

    win = StudioWindow(settings=settings)
    win.open(datasets.path("modem_tiny"))
    win.resize(1280, 820)
    win.show()
    app.processEvents()
    areas = win.view.stats.findChildren(QScrollArea)
    assert len(areas) == 1
    assert not areas[0].verticalScrollBar().isVisible()
    # a short window scrolls the statistics
    win.resize(1280, 420)
    app.processEvents()
    assert areas[0].verticalScrollBar().isVisible()
    # the start page scrolls when smaller than its card
    win.show_welcome()
    win.resize(win.minimumSizeHint().width(), 300)
    app.processEvents()
    page = win.welcome.findChild(QScrollArea)
    assert page.verticalScrollBar().isVisible()
    win.close()


def test_view_that_cannot_be_drawn_is_reported(app, monkeypatch):
    from pcsf.studio import figures

    view = ModelView()
    view.set_model(open_source(datasets.path("occam2d_tiny")))
    messages = []
    view.plot_failed.connect(messages.append)

    def broken(*args, **kwargs):
        raise ValueError("bad geometry")

    monkeypatch.setattr(figures, "draw", broken)
    view.redraw()  # does not raise
    assert len(messages) == 1 and "bad geometry" in messages[0]
    assert "bad geometry" in view.figure.texts[0].get_text()
    monkeypatch.undo()
    view.redraw()
    assert not view.figure.texts
    # a reversed colour range is drawn with a valid one
    view.auto_range.setChecked(False)
    view.vmin.setValue(3.0)
    view.vmax.setValue(1.0)
    lo, hi = view.figure.axes[0].collections[0].get_clim()
    assert lo == 3.0 and hi > lo
    assert len(messages) == 1


def test_plot_toolbar_icons_follow_theme(app, settings):
    # matplotlib draws white icons when the toolbar background is
    # dark; a transparent background counted as dark (regression)
    from pcsf.studio.style import DARK, LIGHT

    win = StudioWindow(settings=settings, theme="light")
    for theme, dark in ((LIGHT, False), (DARK, True)):
        win.set_theme(theme.name)
        nav = win.view.nav
        back = nav.palette().color(nav.backgroundRole())
        assert back.name() == theme.panel
        assert (back.value() < 128) is dark
