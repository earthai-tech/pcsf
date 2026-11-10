"""Qt widgets of PCSF Studio.

:class:`ModelView` shows one model, an inspector beside a plot, and
can be embedded in another Qt application (pyCSAMT's desktop app
uses it this way). :class:`StudioWindow` is the standalone window
around it: file menu, drag and drop, conversion and exports.

The widgets only display what :mod:`pcsf.studio.figures` draws and
:mod:`pcsf.studio.summary` tabulates; they hold no format logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..api import write
from . import figures, summary
from .sources import LoadedModel, open_source

__all__ = ["ModelView", "StudioWindow"]

#: Application icon shipped with the package.
ICON = (
    Path(__file__).resolve().parent / "resources" / "pcsf-studio.png"
)

#: Colour maps offered in the plot panel.
CMAPS = ("jet_r", "viridis", "turbo_r", "RdYlBu", "Spectral", "gray")

_OPEN_FILTER = (
    "PCSF and solver files (*.pcsf *.pcsm *.gz *.nc *.rho "
    "*.resistivity);;All files (*)"
)


def _table(header: list[str], rows: list[list[Any]]) -> QTableWidget:
    t = QTableWidget(len(rows), len(header))
    t.setHorizontalHeaderLabels(header)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.verticalHeader().setVisible(False)
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


class ModelView(QWidget):
    """Inspector and plot of one PCSF model.

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
        self.loaded: LoadedModel | None = None
        self.figure = Figure(figsize=(7, 5), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.tabs = QTabWidget()
        self._build()

    # -------------------------------------------------------- layout
    def _build(self) -> None:
        self.view_box = QComboBox()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.position = QLabel()
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
        self.stations_box = QCheckBox("Stations")
        self.stations_box.setChecked(True)
        self.fit_box = QCheckBox("Fit to survey")
        self.depth = QDoubleSpinBox()
        self.depth.setRange(0.0, 1e7)
        self.depth.setDecimals(0)
        self.depth.setSingleStep(100.0)
        self.depth.setSpecialValueText("whole model")
        self.depth.setSuffix(" m")

        controls = QFormLayout()
        controls.addRow("View", self.view_box)
        pos = QHBoxLayout()
        pos.addWidget(self.slider, 1)
        pos.addWidget(self.position)
        controls.addRow("Position", pos)
        controls.addRow("Colour map", self.cmap_box)
        rng = QHBoxLayout()
        rng.addWidget(self.auto_range)
        rng.addWidget(self.vmin)
        rng.addWidget(QLabel("to"))
        rng.addWidget(self.vmax)
        controls.addRow("log10 rho range", rng)
        controls.addRow("Depth limit", self.depth)
        opts = QHBoxLayout()
        opts.addWidget(self.stations_box)
        opts.addWidget(self.fit_box)
        opts.addStretch(1)
        controls.addRow("", opts)

        plot = QWidget()
        pl = QVBoxLayout(plot)
        pl.addWidget(NavigationToolbar2QT(self.canvas, plot))
        pl.addWidget(self.canvas, 1)
        pl.addLayout(controls)

        split = QSplitter()
        split.addWidget(self.tabs)
        split.addWidget(plot)
        split.setStretchFactor(1, 2)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(split)

        self.view_box.currentTextChanged.connect(self._view_changed)
        self.slider.valueChanged.connect(self.redraw)
        self.cmap_box.currentTextChanged.connect(self.redraw)
        self.auto_range.toggled.connect(self._range_toggled)
        self.vmin.valueChanged.connect(self.redraw)
        self.vmax.valueChanged.connect(self.redraw)
        self.stations_box.toggled.connect(self.redraw)
        self.fit_box.toggled.connect(self.redraw)
        self.depth.valueChanged.connect(self.redraw)

    # --------------------------------------------------------- model
    def set_model(self, loaded: LoadedModel) -> None:
        """Show a model.

        Parameters
        ----------
        loaded : LoadedModel
            Result of :func:`~pcsf.studio.sources.open_source`.
        """
        self.loaded = loaded
        model = loaded.model
        self._fill_tabs(loaded)
        lo, hi = figures.color_range(model)
        for box, value in ((self.vmin, lo), (self.vmax, hi)):
            box.blockSignals(True)
            box.setValue(value)
            box.blockSignals(False)
        self.view_box.blockSignals(True)
        self.view_box.clear()
        self.view_box.addItems(figures.views(model))
        self.view_box.blockSignals(False)
        self._view_changed(self.view_box.currentText())
        self.model_changed.emit(loaded)

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

    # ---------------------------------------------------------- plot
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
        """Draw the current view with the current options."""
        if self.loaded is None or not self.view_box.currentText():
            return
        model = self.loaded.model
        view = self.view_box.currentText()
        index = self.slider.value()
        auto = self.auto_range.isChecked()
        figures.draw(
            self.figure,
            model,
            view,
            index,
            cmap=self.cmap_box.currentText(),
            vmin=None if auto else self.vmin.value(),
            vmax=None if auto else self.vmax.value(),
            show_stations=self.stations_box.isChecked(),
            max_depth=self.depth.value() or None,
            fit=self.fit_box.isChecked(),
        )
        self.position.setText(
            figures.position_label(model, view, index)
        )
        self.canvas.draw_idle()


class StudioWindow(QMainWindow):
    """Main window of PCSF Studio.

    Parameters
    ----------
    path : path-like, optional
        File or run folder opened at start.
    """

    def __init__(self, path: Any = None) -> None:
        super().__init__()
        self.setWindowTitle("PCSF Studio")
        self.resize(1200, 760)
        self.setAcceptDrops(True)
        self.view = ModelView()
        self.setCentralWidget(self.view)
        self._actions()
        self.statusBar().showMessage(
            "Open a .pcsf or .pcsm file, a solver file or a run "
            "folder (File menu or drag and drop)."
        )
        if path is not None:
            self.open(path)

    def _actions(self) -> None:
        menu = self.menuBar().addMenu("&File")

        def add(text, slot, key=None, enabled=True):
            act = QAction(text, self)
            if key is not None:
                act.setShortcut(QKeySequence(key))
            act.triggered.connect(slot)
            act.setEnabled(enabled)
            menu.addAction(act)
            return act

        add(
            "&Open file...",
            self._open_file,
            QKeySequence.StandardKey.Open,
        )
        add("Open run &folder...", self._open_folder)
        menu.addSeparator()
        self._model_actions = [
            add(
                "&Save as PCSF or PCSM...",
                self._save_as,
                QKeySequence.StandardKey.SaveAs,
                False,
            ),
            add("Export &figure...", self._export_figure, None, False),
            add(
                "Export &cells (CSV)...",
                self._export_cells,
                None,
                False,
            ),
            add(
                "Export s&tations (CSV)...",
                self._export_stations,
                None,
                False,
            ),
        ]
        menu.addSeparator()
        add("&Quit", self.close, QKeySequence.StandardKey.Quit)
        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("&About PCSF Studio", self)
        about.triggered.connect(self._about)
        help_menu.addAction(about)

    # ------------------------------------------------------------ open
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
        self.setWindowTitle(f"PCSF Studio - {loaded.title}")
        for act in self._model_actions:
            act.setEnabled(True)
        note = (
            f"; {len(loaded.warnings)} reading note(s)"
            if loaded.warnings
            else ""
        )
        self.statusBar().showMessage(
            f"{loaded.path} ({loaded.kind}, {loaded.model.kind}){note}"
        )
        return True

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", _OPEN_FILTER
        )
        if path:
            self.open(path)

    def _open_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Open run folder"
        )
        if path:
            self.open(path)

    def dragEnterEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: Any) -> None:
        urls = event.mimeData().urls()
        if urls:
            self.open(urls[0].toLocalFile())

    # ---------------------------------------------------------- export
    def _target(
        self, title: str, suffix: str, filt: str
    ) -> Path | None:
        loaded = self.view.loaded
        stem = loaded.path.name.split(".")[0] if loaded else "model"
        path, _ = QFileDialog.getSaveFileName(
            self, title, f"{stem}{suffix}", filt
        )
        return Path(path) if path else None

    def _done(self, path: Path) -> None:
        self.statusBar().showMessage(f"Wrote {path}")

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
        self._done(dst)

    def _about(self) -> None:
        import matplotlib
        import PySide6

        QMessageBox.about(
            self,
            "About PCSF Studio",
            f"PCSF Studio {__version__}\n\n"
            "Viewer and inspector for the Portable Common Subsurface "
            "Format.\n\n"
            f"PySide6 {PySide6.__version__}, matplotlib "
            f"{matplotlib.__version__}\nBSD-3-Clause licence",
        )


def application() -> QApplication:
    """Return the running QApplication, creating one if needed."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        app.setApplicationName("PCSF Studio")
        if ICON.exists():
            app.setWindowIcon(QIcon(str(ICON)))
    return app
