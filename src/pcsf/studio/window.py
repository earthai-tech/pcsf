"""Qt widgets of PCSF Studio.

:class:`ModelView` shows one model and can be embedded in another Qt
application (pyCSAMT's desktop app uses it this way):

- a header card with the file name and status chips (geometry kind,
  solver, cells, stations, conformance, inversion record);
- the inspector (summary, stations, metadata, inversion record,
  conformance, reading notes) on the left;
- the plot with its controls in the centre;
- statistics of the whole model and of the current view, with a
  histogram of :math:`\\log_{10}\\rho`, on the right.

:class:`StudioWindow` is the standalone application around it: a
toolbar (open, samples, save, export, and the help menu behind the
logo at the far right), a welcome page with recent files, and drag
and drop.

The widgets only display what :mod:`pcsf.studio.figures` draws and
:mod:`pcsf.studio.summary` computes; they hold no format logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)
from matplotlib.figure import Figure
from PySide6.QtCore import QSettings, QSize, Qt, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QDesktopServices,
    QIcon,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import __version__, datasets
from ..api import write
from . import figures, summary
from .sources import LoadedModel, open_source
from .style import ACCENT, STYLE_SHEET

__all__ = ["ModelView", "StudioWindow", "application"]

_RES = Path(__file__).resolve().parent / "resources"
#: Logo of PCSF Studio (vector); ``ICON_PNG`` is its 256 px render.
ICON_SVG = _RES / "pcsf-studio.svg"
ICON_PNG = _RES / "pcsf-studio.png"
#: Kept for code written against the first version.
ICON = ICON_PNG

#: Symbols used in labels (Greek rho, subscript one and zero).
RHO = "\N{GREEK SMALL LETTER RHO}"
LOG10_RHO = "log\N{SUBSCRIPT ONE}\N{SUBSCRIPT ZERO}" + RHO

#: Colour maps offered in the plot panel.
CMAPS = ("jet_r", "viridis", "turbo_r", "RdYlBu", "Spectral", "gray")
#: Links of the help menu.
DOCS_URL = "https://github.com/earthai-tech/pcsf"
SPEC_URL = "https://github.com/earthai-tech/pcsf/tree/master/spec"
MAX_RECENT = 8

_OPEN_FILTER = (
    "PCSF and solver files (*.pcsf *.pcsm *.gz *.nc *.rho "
    "*.resistivity);;All files (*)"
)


def logo_icon() -> QIcon:
    """The logo as an icon, from the SVG when Qt can render it."""
    for path in (ICON_SVG, ICON_PNG):
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return QIcon()


# ------------------------------------------------------------- helpers
def _label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    return lab


def _card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(6)
    return frame, lay


def _table(header: list[str], rows: list[list[Any]]) -> QTableWidget:
    t = QTableWidget(len(rows), len(header))
    t.setHorizontalHeaderLabels(header)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(False)
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            text = (
                f"{value:.6g}"
                if isinstance(value, float)
                else str(value)
            )
            t.setItem(i, j, QTableWidgetItem(text))
    t.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )
    t.horizontalHeader().setStretchLastSection(True)
    return t


def _fill_tree(parent: Any, value: Any) -> None:
    for key, sub in value.items():
        if isinstance(sub, dict):
            item = QTreeWidgetItem(parent, [key, ""])
            _fill_tree(item, sub)
        else:
            QTreeWidgetItem(parent, [key, str(sub)])


def _num(value: float) -> str:
    """Three significant figures, with k and M from ten thousand."""
    a = abs(value)
    if 1e4 <= a < 1e6:
        return f"{value / 1e3:.3g} k"
    if 1e6 <= a < 1e9:
        return f"{value / 1e6:.3g} M"
    return f"{value:.3g}"


def _rho(value: float | None) -> str:
    """Resistivity for display, e.g. ``2.26 kΩ·m``."""
    if value is None:
        return "-"
    text = _num(value)
    sep = "" if text.endswith(("k", "M")) else " "
    return f"{text}{sep}Ω·m"


class _Tile(QFrame):
    """A small label-and-value box of the statistics panel."""

    def __init__(self, label: str) -> None:
        super().__init__()
        self.setObjectName("Tile")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(0)
        lay.addWidget(_label(label, "TileLabel"))
        self.value = _label("-", "TileValue")
        lay.addWidget(self.value)

    def set(self, text: str, tip: str = "") -> None:
        self.value.setText(text)
        self.setToolTip(tip)


class _StatsBlock(QWidget):
    """Tiles describing one set of values (model or view)."""

    FIELDS = (
        ("cells", "Cells"),
        ("air", "Air / missing"),
        ("median", f"Median {RHO}"),
        ("range", f"{RHO} range (5-95 %)"),
        ("mean", f"Mean {LOG10_RHO}"),
        ("std", "Spread (std)"),
    )

    def __init__(self) -> None:
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        self.tiles = {}
        for i, (key, label) in enumerate(self.FIELDS):
            tile = _Tile(label)
            self.tiles[key] = tile
            grid.addWidget(tile, i // 2, i % 2)

    def show_stats(self, s: dict[str, Any]) -> None:
        t = self.tiles
        t["cells"].set(f"{s['n_earth']:,}", f"{s['n']:,} values")
        t["air"].set(f"{s['n_air']:,} / {s['n_missing']:,}")
        t["median"].set(_rho(s["median"]))
        if s["p05"] is None:
            t["range"].set("-")
        else:
            t["range"].set(
                f"{_num(s['p05'])} \u2013 {_num(s['p95'])}",
                f"min {_rho(s['min'])}, max {_rho(s['max'])}",
            )
        mean, std = s["log10_mean"], s["log10_std"]
        t["mean"].set("-" if mean is None else f"{mean:.2f}")
        t["std"].set("-" if std is None else f"{std:.2f} dec")


class _StatsPanel(QWidget):
    """Statistics of the model and of the current view."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumWidth(250)
        self.setMaximumWidth(330)
        card, lay = _card()
        lay.addWidget(_label("STATISTICS", "Section"))
        lay.addWidget(_label("Whole model", "Muted"))
        self.model_block = _StatsBlock()
        lay.addWidget(self.model_block)
        lay.addSpacing(4)
        self.view_title = _label("Current view", "Muted")
        lay.addWidget(self.view_title)
        self.view_block = _StatsBlock()
        lay.addWidget(self.view_block)
        lay.addSpacing(4)
        lay.addWidget(_label(f"Distribution of {LOG10_RHO}", "Muted"))
        self.hist_fig = Figure(
            figsize=(2.6, 1.7), layout="constrained"
        )
        self.hist = FigureCanvasQTAgg(self.hist_fig)
        self.hist.setMinimumHeight(150)
        lay.addWidget(self.hist)
        lay.addStretch(1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
        self._model_logs = np.array([])

    def set_model(self, model: Any) -> None:
        values = figures._model_values(model)
        self.model_block.show_stats(summary.value_stats(values))
        self._model_logs = _earth_logs(values)

    def set_view(
        self, label: str, values: np.ndarray, vmin: float, vmax: float
    ) -> None:
        self.view_title.setText(f"Current view: {label}")
        self.view_block.show_stats(summary.value_stats(values))
        fig = self.hist_fig
        fig.clear()
        ax = fig.add_subplot(1, 1, 1)
        view_logs = _earth_logs(values)
        both = np.concatenate([self._model_logs, view_logs])
        if both.size:
            bins = np.linspace(both.min(), both.max() + 1e-9, 31)
            ax.hist(
                self._model_logs,
                bins=bins,
                color="#c9cfdb",
                label="model",
                density=True,
            )
            if view_logs.size:
                ax.hist(
                    view_logs,
                    bins=bins,
                    color=ACCENT,
                    alpha=0.75,
                    label="view",
                    density=True,
                )
            for v in (vmin, vmax):
                ax.axvline(v, color="#1f2533", lw=0.8, ls="--")
        ax.set_yticks([])
        ax.tick_params(labelsize=7)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        if both.size:
            ax.legend(
                fontsize=6.5,
                frameon=False,
                ncol=2,
                loc="lower left",
                bbox_to_anchor=(0.0, 1.0),
                borderaxespad=0.0,
            )
        self.hist.draw_idle()


def _earth_logs(values: Any) -> np.ndarray:
    rho = np.ravel(np.asarray(values, dtype=float))
    ok = (
        np.isfinite(rho)
        & (rho > 0)
        & (rho < figures.AIR_THRESHOLD_OHM_M)
    )
    return np.log10(rho[ok])


# ----------------------------------------------------------- ModelView
class ModelView(QWidget):
    """Header, inspector, plot and statistics of one PCSF model.

    Parameters
    ----------
    parent : QWidget, optional
        Parent widget.

    Attributes
    ----------
    loaded : LoadedModel or None
        Model shown, set by :meth:`set_model`.
    figure : matplotlib.figure.Figure
        Figure of the plot panel.
    tabs : QTabWidget
        Inspector tabs.

    Notes
    -----
    Signal ``model_changed(object)`` is emitted with the
    :class:`~pcsf.studio.sources.LoadedModel` after each
    :meth:`set_model`.

    Examples
    --------
    Embedding in another application::

        from pcsf.studio import ModelView
        from pcsf.studio.sources import open_source

        view = ModelView()
        view.set_model(open_source("model.pcsf"))
        layout.addWidget(view)
    """

    model_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        self.loaded: LoadedModel | None = None
        self.figure = Figure(figsize=(7, 5), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.tabs = QTabWidget()
        self.stats = _StatsPanel()
        self._build()

    # ------------------------------------------------- layout
    def _header(self) -> QFrame:
        card, lay = _card()
        row = QHBoxLayout()
        self.title = _label("", "Title")
        row.addWidget(self.title)
        row.addStretch(1)
        lay.addLayout(row)
        self.subtitle = _label("", "Subtitle")
        self.subtitle.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        lay.addWidget(self.subtitle)
        self.chips = QHBoxLayout()
        self.chips.setSpacing(6)
        lay.addLayout(self.chips)
        return card

    def _controls(self) -> QWidget:
        self.view_box = QComboBox()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.position = _label("", "Muted")
        self.position.setMinimumWidth(110)
        self.cmap_box = QComboBox()
        self.cmap_box.addItems(CMAPS)
        self.auto_range = QCheckBox("Auto")
        self.auto_range.setChecked(True)
        self.vmin = QDoubleSpinBox()
        self.vmax = QDoubleSpinBox()
        for box in (self.vmin, self.vmax):
            box.setRange(-10.0, 20.0)
            box.setDecimals(2)
            box.setSingleStep(0.1)
            box.setEnabled(False)
        self.depth = QDoubleSpinBox()
        self.depth.setRange(0.0, 1e7)
        self.depth.setDecimals(0)
        self.depth.setSingleStep(100.0)
        self.depth.setSpecialValueText("whole model")
        self.depth.setSuffix(" m")
        self.stations_box = QCheckBox("Stations")
        self.stations_box.setChecked(True)
        self.fit_box = QCheckBox("Fit to survey")

        box = QWidget()
        grid = QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(_label("View", "Muted"), 0, 0)
        grid.addWidget(self.view_box, 0, 1)
        grid.addWidget(_label("Position", "Muted"), 0, 2)
        grid.addWidget(self.slider, 0, 3)
        grid.addWidget(self.position, 0, 4)
        grid.addWidget(_label("Colours", "Muted"), 1, 0)
        grid.addWidget(self.cmap_box, 1, 1)
        grid.addWidget(_label(LOG10_RHO, "Muted"), 1, 2)
        rng = QHBoxLayout()
        rng.addWidget(self.auto_range)
        rng.addWidget(self.vmin)
        rng.addWidget(_label("to", "Muted"))
        rng.addWidget(self.vmax)
        rng.addSpacing(10)
        rng.addWidget(_label("Depth", "Muted"))
        rng.addWidget(self.depth)
        rng.addStretch(1)
        grid.addLayout(rng, 1, 3, 1, 2)
        opts = QHBoxLayout()
        opts.addWidget(self.stations_box)
        opts.addWidget(self.fit_box)
        opts.addStretch(1)
        grid.addLayout(opts, 2, 1, 1, 4)
        grid.setColumnStretch(3, 1)
        return box

    def _build(self) -> None:
        plot_card, plot_lay = _card()
        plot_lay.addWidget(NavigationToolbar2QT(self.canvas, self))
        plot_lay.addWidget(self.canvas, 1)
        plot_lay.addWidget(self._controls())

        self.tabs.setMinimumWidth(260)
        split = QSplitter()
        split.addWidget(self.tabs)
        split.addWidget(plot_card)
        split.addWidget(self.stats)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        split.setSizes([320, 760, 280])

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)
        lay.addWidget(self._header())
        lay.addWidget(split, 1)

        self.view_box.currentTextChanged.connect(self._view_changed)
        self.slider.valueChanged.connect(self.redraw)
        self.cmap_box.currentTextChanged.connect(self.redraw)
        self.auto_range.toggled.connect(self._range_toggled)
        self.vmin.valueChanged.connect(self.redraw)
        self.vmax.valueChanged.connect(self.redraw)
        self.stations_box.toggled.connect(self.redraw)
        self.fit_box.toggled.connect(self.redraw)
        self.depth.valueChanged.connect(self.redraw)

    # -------------------------------------------------- model
    def set_model(self, loaded: LoadedModel) -> None:
        """Show a model.

        Parameters
        ----------
        loaded : LoadedModel
            Result of :func:`~pcsf.studio.sources.open_source`.
        """
        self.loaded = loaded
        model = loaded.model
        self._fill_header(loaded)
        self._fill_tabs(loaded)
        self.stats.set_model(model)
        lo, hi = figures.color_range(model)
        # A depth limit belongs to one model; start each one whole.
        for box, value in (
            (self.vmin, lo),
            (self.vmax, hi),
            (self.depth, 0.0),
        ):
            box.blockSignals(True)
            box.setValue(value)
            box.blockSignals(False)
        self.view_box.blockSignals(True)
        self.view_box.clear()
        self.view_box.addItems(figures.views(model))
        self.view_box.blockSignals(False)
        self._view_changed(self.view_box.currentText())
        self.model_changed.emit(loaded)

    def _chip(
        self, text: str, status: str = "", tip: str = ""
    ) -> None:
        chip = _label(text, "Chip")
        if status:
            chip.setProperty("status", status)
        chip.setToolTip(tip)
        self.chips.addWidget(chip)

    def _fill_header(self, loaded: LoadedModel) -> None:
        model = loaded.model
        self.title.setText(loaded.path.name)
        desc = model.description or "no description"
        self.subtitle.setText(f"{loaded.path.parent}  •  {desc}")
        while self.chips.count():
            item = self.chips.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        d = summary.summary_rows(model)
        rows = dict(d)
        self._chip(model.kind)
        if model.source_backend:
            self._chip(model.source_backend)
        self._chip(f"{rows.get('Cells', '-')} cells")
        self._chip(f"{rows.get('Stations', '0')} stations")
        conf = summary.conformance_rows(model)
        ok = sum(1 for _, passed, _ in conf if passed)
        self._chip(
            f"conformance {ok}/{len(conf)}",
            "good" if ok == len(conf) else "bad",
            "Rules of the PCSF specification",
        )
        _, req, rec = summary.record_rows(model)
        if req:
            self._chip(
                f"record: {len(req)} required missing",
                "warn",
                ", ".join(req),
            )
        else:
            self._chip(
                "record complete"
                if not rec
                else f"record: {len(rec)} recommended missing",
                "good" if not rec else "warn",
                ", ".join(rec),
            )
        if loaded.warnings:
            self._chip(
                f"{len(loaded.warnings)} reading note(s)",
                "warn",
                "\n".join(loaded.warnings),
            )
        self.chips.addStretch(1)

    def _fill_tabs(self, loaded: LoadedModel) -> None:
        model = loaded.model
        self.tabs.clear()
        self.tabs.addTab(
            _table(
                ["Field", "Value"],
                [
                    list(r)
                    for r in summary.summary_rows(model, loaded.title)
                ],
            ),
            "Summary",
        )
        header, rows = summary.station_rows(model)
        self.tabs.addTab(_table(header, rows), "Stations")
        tree = QTreeWidget()
        tree.setHeaderLabels(["Key", "Value"])
        _fill_tree(
            tree.invisibleRootItem(), summary.metadata_tree(model)
        )
        tree.expandToDepth(0)
        self.tabs.addTab(tree, "Metadata")
        rows, req, rec = summary.record_rows(model)
        body = [list(r) for r in rows]
        body += [[f, "missing (required)"] for f in req]
        body += [[f, "missing (recommended)"] for f in rec]
        self.tabs.addTab(_table(["Field", "Value"], body), "Record")
        conf = summary.conformance_rows(model)
        self.tabs.addTab(
            _table(
                ["Rule", "Result", "Message"],
                [
                    [r, "pass" if ok else "FAIL", m]
                    for r, ok, m in conf
                ],
            ),
            "Conformance",
        )
        if loaded.warnings or loaded.files:
            notes = [[w] for w in loaded.warnings]
            notes += [[f"read {p}"] for p in loaded.files]
            self.tabs.addTab(_table(["Note"], notes), "Reading")

    # --------------------------------------------------- plot
    def _view_changed(self, view: str) -> None:
        if self.loaded is None or not view:
            return
        n = figures.n_positions(self.loaded.model, view)
        self.slider.blockSignals(True)
        self.slider.setRange(0, n - 1)
        self.slider.setValue(n // 2 if view == "depth slice" else 0)
        self.slider.blockSignals(False)
        self.slider.setEnabled(n > 1)
        self.redraw()

    def _range_toggled(self, auto: bool) -> None:
        self.vmin.setEnabled(not auto)
        self.vmax.setEnabled(not auto)
        self.redraw()

    def redraw(self, *_: Any) -> None:
        """Draw the current view and update its statistics."""
        if self.loaded is None or not self.view_box.currentText():
            return
        model = self.loaded.model
        view = self.view_box.currentText()
        index = self.slider.value()
        auto = self.auto_range.isChecked()
        if auto:
            vmin, vmax = figures.color_range(model)
        else:
            vmin, vmax = self.vmin.value(), self.vmax.value()
        figures.draw(
            self.figure,
            model,
            view,
            index,
            cmap=self.cmap_box.currentText(),
            vmin=vmin,
            vmax=vmax,
            show_stations=self.stations_box.isChecked(),
            max_depth=self.depth.value() or None,
            fit=self.fit_box.isChecked(),
        )
        label = figures.position_label(model, view, index)
        self.position.setText(label)
        self.stats.set_view(
            f"{view}{', ' + label if label else ''}",
            figures.view_values(model, view, index),
            vmin,
            vmax,
        )
        self.canvas.draw_idle()


# -------------------------------------------------------- welcome page
class _Welcome(QWidget):
    """First page: logo, actions, samples and recent files."""

    def __init__(self, window: StudioWindow) -> None:
        super().__init__()
        self.setObjectName("Page")
        card, lay = _card()
        card.setMaximumWidth(620)
        logo = QLabel()
        logo.setPixmap(logo_icon().pixmap(QSize(96, 96)))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)
        title = _label("PCSF Studio", "Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        sub = _label(
            "View and inspect electromagnetic inversion models in the "
            "Portable Common Subsurface Format, and the native files "
            "of Occam2D, ModEM, MARE2DEM and the EMC.",
            "Subtitle",
            wrap=True,
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        lay.addSpacing(8)
        row = QHBoxLayout()
        row.addStretch(1)
        open_btn = QPushButton("Open file...")
        open_btn.setObjectName("Primary")
        open_btn.clicked.connect(window.open_file)
        folder_btn = QPushButton("Open run folder...")
        folder_btn.clicked.connect(window.open_folder)
        sample_btn = QPushButton("Try a sample")
        sample_btn.setMenu(window.samples_menu)
        for b in (open_btn, folder_btn, sample_btn):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addSpacing(8)
        lay.addWidget(_label("RECENT", "Section"))
        self.recent = QListWidget()
        self.recent.setObjectName("Recent")
        self.recent.setMaximumHeight(190)
        self.recent.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.recent.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.recent.setUniformItemSizes(True)
        self.recent.itemActivated.connect(
            lambda item: window.open(
                item.data(Qt.ItemDataRole.UserRole)
            )
        )
        lay.addWidget(self.recent)
        hint = _label(
            "Or drop a file or a run folder on this window.", "Muted"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        ver = _label(f"pcsf {__version__}", "Muted")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ver)
        outer = QVBoxLayout(self)
        outer.addStretch(1)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(card)
        h.addStretch(1)
        outer.addLayout(h)
        outer.addStretch(2)

    def set_recent(self, paths: list[str]) -> None:
        self.recent.clear()
        for p in paths:
            item = QListWidgetItem(f"{Path(p).name}\n{Path(p).parent}")
            item.setToolTip(p)
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.recent.addItem(item)
        if not paths:
            self.recent.addItem("No recent files")


# ------------------------------------------------------- main window
class StudioWindow(QMainWindow):
    """Main window of PCSF Studio.

    Parameters
    ----------
    path : path-like, optional
        File or run folder opened at start.
    settings : QSettings, optional
        Where recent files are kept; the user settings of
        ``earthai-tech/PCSF Studio`` by default.
    """

    def __init__(
        self, path: Any = None, settings: QSettings | None = None
    ) -> None:
        super().__init__()
        self.setWindowTitle("PCSF Studio")
        self.setWindowIcon(logo_icon())
        self.resize(1400, 860)
        self.setAcceptDrops(True)
        self.setStyleSheet(STYLE_SHEET)
        self.settings = settings or QSettings(
            "earthai-tech", "PCSF Studio"
        )
        self.samples_menu = self._samples_menu()
        self.view = ModelView()
        self.welcome = _Welcome(self)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.welcome)
        self.pages.addWidget(self.view)
        self.setCentralWidget(self.pages)
        self._toolbar()
        self._menus()
        self._refresh_recent()
        self.statusBar().showMessage("Ready")
        if path is not None:
            self.open(path)

    # ------------------------------------------------ actions
    def _action(
        self,
        text: str,
        slot: Any,
        key: Any = None,
        enabled: bool = True,
        tip: str = "",
    ) -> QAction:
        act = QAction(text, self)
        if key is not None:
            act.setShortcut(QKeySequence(key))
        act.triggered.connect(slot)
        act.setEnabled(enabled)
        act.setToolTip(tip or text)
        return act

    def _samples_menu(self) -> QMenu:
        menu = QMenu("Samples", self)
        labels = {
            "occam2d_tiny": "Occam2D run (2D grid)",
            "modem_tiny": "ModEM run (3D grid)",
            "mare2dem_tiny": "MARE2DEM run (triangular mesh)",
        }
        for name in datasets.NAMES:
            act = QAction(labels.get(name, name), self)
            act.triggered.connect(
                lambda _=False, n=name: self.open(datasets.path(n))
            )
            menu.addAction(act)
        return menu

    def _toolbar(self) -> None:
        bar = QToolBar("Main")
        bar.setObjectName("MainBar")
        bar.setMovable(False)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(bar)
        self.open_act = self._action(
            "Open",
            self.open_file,
            QKeySequence.StandardKey.Open,
            tip="Open a .pcsf/.pcsm file or a solver file (Ctrl+O)",
        )
        self.folder_act = self._action(
            "Open folder",
            self.open_folder,
            "Ctrl+Shift+O",
            tip="Open an Occam2D, ModEM or MARE2DEM run folder",
        )
        bar.addAction(self.open_act)
        bar.addAction(self.folder_act)
        samples = QToolButton()
        samples.setText("Samples")
        samples.setMenu(self.samples_menu)
        samples.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        bar.addWidget(samples)
        bar.addSeparator()
        self.save_act = self._action(
            "Save as",
            self._save_as,
            QKeySequence.StandardKey.SaveAs,
            False,
            "Save as PCSF, PCSM or PCSM gzip (Ctrl+Shift+S)",
        )
        bar.addAction(self.save_act)
        self.export_menu = QMenu("Export", self)
        self.fig_act = self._action(
            "Figure (PNG, SVG, PDF)...",
            self._export_figure,
            "Ctrl+E",
            False,
        )
        self.cells_act = self._action(
            "Cells (CSV)...", self._export_cells, None, False
        )
        self.stations_act = self._action(
            "Stations (CSV)...", self._export_stations, None, False
        )
        for act in (self.fig_act, self.cells_act, self.stations_act):
            self.export_menu.addAction(act)
        export = QToolButton()
        export.setText("Export")
        export.setMenu(self.export_menu)
        export.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.export_button = export
        export.setEnabled(False)
        bar.addWidget(export)
        self.home_act = self._action(
            "Start page",
            self.show_welcome,
            tip="Back to the start page",
        )
        bar.addSeparator()
        bar.addAction(self.home_act)

        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        bar.addWidget(spacer)
        self.help_menu = QMenu("Help", self)
        self.help_menu.addAction(
            self._action("About PCSF Studio", self._about)
        )
        self.help_menu.addAction(
            self._action("Keyboard shortcuts", self._shortcuts, "F1")
        )
        self.help_menu.addSeparator()
        self.help_menu.addAction(
            self._action("Documentation", lambda: self._link(DOCS_URL))
        )
        self.help_menu.addAction(
            self._action(
                "Format specification", lambda: self._link(SPEC_URL)
            )
        )
        helpb = QToolButton()
        helpb.setObjectName("HelpButton")
        helpb.setIcon(logo_icon())
        helpb.setIconSize(QSize(22, 22))
        helpb.setText(" ?")
        helpb.setToolTip("Help and about PCSF Studio")
        helpb.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        helpb.setMenu(self.help_menu)
        helpb.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.help_button = helpb
        bar.addWidget(helpb)
        self._model_actions = [
            self.save_act,
            self.fig_act,
            self.cells_act,
            self.stations_act,
        ]

    def _menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        for act in (self.open_act, self.folder_act):
            file_menu.addAction(act)
        file_menu.addMenu(self.samples_menu)
        self.recent_menu = file_menu.addMenu("Recent")
        file_menu.addSeparator()
        file_menu.addAction(self.save_act)
        file_menu.addMenu(self.export_menu)
        file_menu.addSeparator()
        file_menu.addAction(
            self._action(
                "Quit", self.close, QKeySequence.StandardKey.Quit
            )
        )
        self.menuBar().addMenu(self.help_menu)

    # ------------------------------------------------- recent
    def _recent(self) -> list[str]:
        value = self.settings.value("recent", [])
        if isinstance(value, str):
            value = [value]
        return [p for p in (value or []) if Path(p).exists()]

    def _remember(self, path: Path) -> None:
        items = [str(path)] + [
            p for p in self._recent() if p != str(path)
        ]
        self.settings.setValue("recent", items[:MAX_RECENT])
        self._refresh_recent()

    def _refresh_recent(self) -> None:
        recent = self._recent()
        self.welcome.set_recent(recent)
        self.recent_menu.clear()
        for p in recent:
            act = QAction(p, self)
            act.triggered.connect(lambda _=False, q=p: self.open(q))
            self.recent_menu.addAction(act)
        self.recent_menu.setEnabled(bool(recent))

    # --------------------------------------------------- open
    def open(self, path: Any) -> bool:
        """Open a file or run folder and show it.

        Parameters
        ----------
        path : path-like
            Passed to :func:`~pcsf.studio.sources.open_source`.

        Returns
        -------
        bool
            True when the model was opened; on failure the error
            is shown in a message box and False is returned.
        """
        try:
            loaded = open_source(path)
        except Exception as exc:  # shown to the user, not hidden
            QMessageBox.critical(
                self,
                "Cannot open",
                f"{Path(path).name}\n\n{type(exc).__name__}: {exc}",
            )
            return False
        self.view.set_model(loaded)
        self.pages.setCurrentWidget(self.view)
        self.setWindowTitle(f"PCSF Studio - {loaded.title}")
        for act in self._model_actions:
            act.setEnabled(True)
        self.export_button.setEnabled(True)
        if not str(loaded.path).startswith(
            str(datasets.path(datasets.NAMES[0]).parent)
        ):
            self._remember(loaded.path)
        note = (
            f"   {len(loaded.warnings)} reading note(s)"
            if loaded.warnings
            else ""
        )
        self.statusBar().showMessage(
            f"{loaded.path}   {loaded.kind} → {loaded.model.kind}"
            f"{note}"
        )
        return True

    def open_file(self) -> None:
        """Ask for a file and open it."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", _OPEN_FILTER
        )
        if path:
            self.open(path)

    def open_folder(self) -> None:
        """Ask for a run folder and open it."""
        path = QFileDialog.getExistingDirectory(
            self, "Open run folder"
        )
        if path:
            self.open(path)

    def show_welcome(self) -> None:
        """Show the start page."""
        self._refresh_recent()
        self.pages.setCurrentWidget(self.welcome)

    def dragEnterEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: Any) -> None:
        urls = event.mimeData().urls()
        if urls:
            self.open(urls[0].toLocalFile())

    # ------------------------------------------------- export
    def _target(
        self, title: str, suffix: str, filt: str
    ) -> Path | None:
        loaded = self.view.loaded
        stem = loaded.path.name.split(".")[0] if loaded else "model"
        path, _ = QFileDialog.getSaveFileName(
            self, title, f"{stem}{suffix}", filt
        )
        return Path(path) if path else None

    def _save_as(self) -> None:
        dst = self._target(
            "Save as",
            ".pcsf",
            "PCSF (*.pcsf);;PCSM (*.pcsm);;PCSM gzip (*.pcsm.gz)",
        )
        if dst is not None:
            self._run(lambda: write(self.view.loaded.model, dst), dst)

    def _export_figure(self) -> None:
        dst = self._target(
            "Export figure",
            ".png",
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)",
        )
        if dst is not None:
            self._run(
                lambda: self.view.figure.savefig(dst, dpi=200), dst
            )

    def _export_cells(self) -> None:
        dst = self._target("Export cells", "_cells.csv", "CSV (*.csv)")
        if dst is not None:
            header, table = summary.cell_table(self.view.loaded.model)
            self._run(
                lambda: summary.write_csv(dst, header, table), dst
            )

    def _export_stations(self) -> None:
        dst = self._target(
            "Export stations", "_stations.csv", "CSV (*.csv)"
        )
        if dst is not None:
            header, rows = summary.station_rows(self.view.loaded.model)
            self._run(
                lambda: summary.write_csv(dst, header, rows), dst
            )

    def _run(self, job: Any, dst: Path) -> None:
        try:
            job()
        except Exception as exc:  # shown to the user, not hidden
            QMessageBox.critical(
                self,
                "Cannot write",
                f"{dst}\n\n{type(exc).__name__}: {exc}",
            )
            return
        self.statusBar().showMessage(f"Wrote {dst}")

    # --------------------------------------------------- help
    def _link(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def _shortcuts(self) -> None:
        QMessageBox.information(
            self,
            "Keyboard shortcuts",
            "Ctrl+O\tOpen file\nCtrl+Shift+O\tOpen run folder\n"
            "Ctrl+Shift+S\tSave as\nCtrl+E\tExport figure\n"
            "F1\tThis list\nCtrl+Q\tQuit\n\n"
            "Drop a file or a folder on the window to open it.",
        )

    def _about(self) -> None:
        import matplotlib
        import PySide6

        box = QMessageBox(self)
        box.setWindowTitle("About PCSF Studio")
        box.setIconPixmap(logo_icon().pixmap(QSize(72, 72)))
        box.setText(f"<b>PCSF Studio {__version__}</b>")
        box.setInformativeText(
            "Viewer and inspector for the Portable Common Subsurface "
            "Format.<br><br>"
            f"PySide6 {PySide6.__version__}, matplotlib "
            f"{matplotlib.__version__}<br>BSD-3-Clause licence<br>"
            f'<a href="{DOCS_URL}">{DOCS_URL}</a>'
        )
        box.exec()


def application() -> QApplication:
    """Return the running QApplication, creating one if needed."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        app.setApplicationName("PCSF Studio")
        app.setOrganizationName("earthai-tech")
        app.setWindowIcon(logo_icon())
    return app
