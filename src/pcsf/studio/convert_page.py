"""Convert page of PCSF Studio: solver runs to PCSF and PCSM.

The page converts any number of sources in one go: run folders and
result files of Occam2D, ModEM and MARE2DEM, EMC netCDF files, and
PCSF or PCSM files (to change their encoding). For each source it
writes the chosen formats, ``.pcsf``, ``.pcsm`` and ``.pcsm.gz``,
next to the source or into one folder, and reports the geometry
kind, the conformance and the reading notes in a log.

The conversions run in a worker thread, one source after another,
so the window stays responsive and a long batch can be stopped
between two sources. The work itself is done by
:func:`pcsf.studio.convert.convert_source`, which needs no Qt.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QSettings, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .convert import FORMATS, ConversionResult, convert_source
from .sources import source_kind
from .style import LIGHT, Theme

__all__ = ["ConvertPage"]

#: Labels of the output formats, in the order shown.
FORMAT_LABELS = {
    "pcsf": "PCSF  (.pcsf, HDF5)",
    "pcsm": "PCSM  (.pcsm, text)",
    "pcsm.gz": "PCSM gzip  (.pcsm.gz)",
}
#: Names of the source kinds in the list.
KIND_LABELS = {
    "occam2d": "Occam2D run",
    "modem": "ModEM model",
    "mare2dem": "MARE2DEM model",
    "emc": "EMC netCDF",
    "pcsf": "PCSF file",
    "pcsm": "PCSM file",
}
_FILE_FILTER = (
    "Solver results and models (*.rho *.resistivity *.nc *.pcsf "
    "*.pcsm *.gz);;All files (*)"
)
_SOURCE, _KIND, _STATUS = range(3)


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("Card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(8)
    head = QLabel(title)
    head.setObjectName("Section")
    lay.addWidget(head)
    return card, lay


def _muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Muted")
    label.setWordWrap(True)
    return label


def _reason(exc: BaseException) -> str:
    text = str(exc).strip() or "no message"
    return f"{type(exc).__name__}: {text}"


class _Worker(QObject):
    """Converts the sources one after another, in a thread."""

    row_started = Signal(int)
    row_done = Signal(int, object)
    row_failed = Signal(int, str)
    finished = Signal()

    def __init__(
        self, jobs: list[tuple[int, Path]], options: dict[str, Any]
    ) -> None:
        super().__init__()
        self.jobs = jobs
        self.options = options
        self.stopped = False

    def run(self) -> None:
        for row, path in self.jobs:
            if self.stopped:
                break
            self.row_started.emit(row)
            try:
                result = convert_source(path, **self.options)
            except Exception as exc:  # reported in the log
                self.row_failed.emit(row, _reason(exc))
            else:
                self.row_done.emit(row, result)
        self.finished.emit()


class ConvertPage(QWidget):
    """Batch conversion of solver output to PCSF and PCSM.

    Parameters
    ----------
    parent : QWidget, optional
        Parent widget.

    Attributes
    ----------
    table : QTableWidget
        The sources: path, kind and status of each.
    format_boxes : dict of str to QCheckBox
        One check box per output format (keys of
        :data:`~pcsf.studio.convert.FORMATS`).
    results : list of ConversionResult
        Results of the last run, in the order of the list.
    start_folder : callable
        Returns the folder the file dialogs open in; set by the
        window to the folder of its most recent file.

    Notes
    -----
    Signal ``open_requested(object)`` is emitted with the first
    file written when "Open the result" is checked; signal
    ``message(str)`` carries a one-line report for a status bar;
    signal ``run_done(int)`` is emitted with the number of sources
    converted when a run ends.

    Examples
    --------
    ::

        page = ConvertPage()
        page.add_sources(["runs/L18PLT", "runs/m_NLCG_100.rho"])
        page.format_boxes["pcsm.gz"].setChecked(True)
        page.start()
    """

    open_requested = Signal(object)
    message = Signal(str)
    run_done = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        self.theme: Theme = LIGHT
        self.results: list[ConversionResult] = []
        self.start_folder: Callable[[], str] = lambda: ""
        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self._failed = 0
        self._build()

    # ------------------------------------------------- layout
    def _build(self) -> None:
        sources, s_lay = _card("SOURCES")
        s_lay.addWidget(
            _muted(
                "Occam2D run folders, ModEM .rho and MARE2DEM "
                ".N.resistivity files (or their run folders), EMC "
                ".nc files, and PCSF or PCSM files to re-encode. "
                "Drop them here or add them with the buttons."
            )
        )
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Source", "Kind", "Status"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(
            _SOURCE, QHeaderView.ResizeMode.Stretch
        )
        for col in (_KIND, _STATUS):
            head.setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.setMinimumHeight(170)
        s_lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.add_files_btn = QPushButton("Add files...")
        self.add_folder_btn = QPushButton("Add run folder...")
        self.remove_btn = QPushButton("Remove")
        self.clear_btn = QPushButton("Clear")
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.remove_btn.clicked.connect(self.remove_selected)
        self.clear_btn.clicked.connect(self.clear)
        for b in (self.add_files_btn, self.add_folder_btn):
            row.addWidget(b)
        row.addStretch(1)
        for b in (self.remove_btn, self.clear_btn):
            row.addWidget(b)
        s_lay.addLayout(row)

        output, o_lay = _card("OUTPUT")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        grid.addWidget(
            _muted("Formats"), 0, 0, Qt.AlignmentFlag.AlignTop
        )
        fmt = QVBoxLayout()
        fmt.setSpacing(4)
        self.format_boxes: dict[str, QCheckBox] = {}
        for key in FORMATS:
            box = QCheckBox(FORMAT_LABELS[key])
            box.setChecked(key == "pcsf")
            box.toggled.connect(self._update_actions)
            self.format_boxes[key] = box
            fmt.addWidget(box)
        grid.addLayout(fmt, 0, 1)
        grid.addWidget(
            _muted("Folder"), 1, 0, Qt.AlignmentFlag.AlignTop
        )
        where = QVBoxLayout()
        where.setSpacing(4)
        self.beside = QRadioButton("Next to each source")
        self.into = QRadioButton("Into this folder:")
        group = QButtonGroup(self)
        group.addButton(self.beside)
        group.addButton(self.into)
        self.beside.setChecked(True)
        where.addWidget(self.beside)
        where.addWidget(self.into)
        pick = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("output folder")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._choose_folder)
        pick.addWidget(self.folder_edit, 1)
        pick.addWidget(self.browse_btn)
        where.addLayout(pick)
        grid.addLayout(where, 1, 1)
        self.into.toggled.connect(self._update_actions)
        self.folder_edit.textChanged.connect(self._update_actions)
        grid.addWidget(
            _muted("Options"), 2, 0, Qt.AlignmentFlag.AlignTop
        )
        opts = QVBoxLayout()
        opts.setSpacing(4)
        self.validate_box = QCheckBox("Check the conformance rules")
        self.validate_box.setChecked(True)
        self.overwrite_box = QCheckBox("Replace existing files")
        self.open_box = QCheckBox("Open the first result when done")
        for box in (
            self.validate_box,
            self.overwrite_box,
            self.open_box,
        ):
            opts.addWidget(box)
        grid.addLayout(opts, 2, 1)
        grid.setColumnStretch(1, 1)
        o_lay.addLayout(grid)
        o_lay.addStretch(1)

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(sources, 3)
        top.addWidget(output, 2)

        log, l_lay = _card("LOG")
        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSizeF(8.5)
        self.log.setFont(font)
        self.log.setMinimumHeight(90)
        l_lay.addWidget(self.log, 1)
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%v / %m")
        self.progress.setValue(0)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setToolTip(
            "Stop after the source being converted"
        )
        self.stop_btn.clicked.connect(self.stop)
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setObjectName("Primary")
        self.convert_btn.clicked.connect(self.start)
        bar.addWidget(self.progress, 1)
        bar.addWidget(self.stop_btn)
        bar.addWidget(self.convert_btn)
        l_lay.addLayout(bar)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)
        lay.addLayout(top, 3)
        lay.addWidget(log, 2)
        self.table.itemSelectionChanged.connect(self._update_actions)
        self._reset_progress()
        self._update_actions()

    def set_theme(self, theme: Theme) -> None:
        """Colours of the status column."""
        self.theme = theme
        for row in range(self.table.rowCount()):
            item = self.table.item(row, _STATUS)
            state = item.data(Qt.ItemDataRole.UserRole)
            self._colour(item, state)

    def _colour(
        self, item: QTableWidgetItem, state: str | None
    ) -> None:
        colour = {
            "done": self.theme.good,
            "warn": self.theme.warn,
            "failed": self.theme.bad,
        }.get(state or "", self.theme.muted)
        item.setForeground(QColor(colour))

    # ------------------------------------------------ sources
    def sources(self) -> list[Path]:
        """Paths in the list, in order."""
        return [
            Path(
                self.table.item(r, _SOURCE).data(
                    Qt.ItemDataRole.UserRole
                )
            )
            for r in range(self.table.rowCount())
        ]

    def add_sources(self, paths: Any) -> int:
        """Add files or folders to the list.

        Parameters
        ----------
        paths : iterable of path-like
            Sources; one already in the list is not added again,
            and one that is not recognised is skipped with a line
            in the log.

        Returns
        -------
        int
            Number of sources added.
        """
        known = {p.resolve() for p in self.sources()}
        added, skipped = 0, []
        for raw in paths:
            path = Path(raw)
            kind = source_kind(path)
            if kind is None:
                skipped.append(path.name or str(path))
                continue
            if path.resolve() in known:
                continue
            known.add(path.resolve())
            row = self.table.rowCount()
            self.table.insertRow(row)
            item = QTableWidgetItem(str(path))
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self.table.setItem(row, _SOURCE, item)
            self.table.setItem(
                row,
                _KIND,
                QTableWidgetItem(KIND_LABELS.get(kind, kind)),
            )
            self._set_status(row, "waiting", None)
            added += 1
        if skipped:
            self._log(
                "Skipped (not a solver run or model file): "
                + ", ".join(skipped)
            )
        if added:
            self._reset_progress()
        self._update_actions()
        return added

    def add_files(self) -> None:
        """Ask for result or model files and add them."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add files", self.start_folder(), _FILE_FILTER
        )
        self.add_sources(paths)

    def add_folder(self) -> None:
        """Ask for a run folder and add it."""
        path = QFileDialog.getExistingDirectory(
            self, "Add run folder", self.start_folder()
        )
        if path:
            self.add_sources([path])

    def remove_selected(self) -> None:
        """Remove the selected rows."""
        rows = sorted(
            {i.row() for i in self.table.selectedIndexes()},
            reverse=True,
        )
        for row in rows:
            self.table.removeRow(row)
        self._reset_progress()
        self._update_actions()

    def clear(self) -> None:
        """Empty the list and the log."""
        self.table.setRowCount(0)
        self.log.clear()
        self.results = []
        self._reset_progress()
        self._update_actions()

    def _reset_progress(self) -> None:
        """Progress of a run not started: 0 of the sources listed."""
        n = self.table.rowCount()
        # a range of (0, 0) would show a busy indicator instead
        self.progress.setRange(0, max(n, 1))
        self.progress.setValue(0)
        self.progress.setFormat("%v / %m" if n else "")

    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Output folder",
            self.folder_edit.text() or self.start_folder(),
        )
        if path:
            self.folder_edit.setText(path)
            self.into.setChecked(True)

    # ------------------------------------------------ options
    def formats(self) -> list[str]:
        """Output formats checked, in the order of the page."""
        return [
            k for k, b in self.format_boxes.items() if b.isChecked()
        ]

    def out_dir(self) -> Path | None:
        """Output folder, or None to write next to each source."""
        text = self.folder_edit.text().strip()
        return Path(text) if self.into.isChecked() and text else None

    def options(self) -> dict[str, Any]:
        """Arguments of :func:`~pcsf.studio.convert.convert_source`."""
        return {
            "formats": self.formats(),
            "out_dir": self.out_dir(),
            "check": self.validate_box.isChecked(),
            "overwrite": self.overwrite_box.isChecked(),
        }

    def save_settings(self, settings: QSettings) -> None:
        """Keep the formats and the output folder."""
        settings.setValue("convert/formats", self.formats())
        settings.setValue("convert/folder", self.folder_edit.text())
        settings.setValue("convert/into", self.into.isChecked())

    def load_settings(self, settings: QSettings) -> None:
        """Restore what :meth:`save_settings` kept."""
        chosen = settings.value("convert/formats")
        if isinstance(chosen, str):
            chosen = [chosen]
        if chosen:
            for key, box in self.format_boxes.items():
                box.setChecked(key in chosen)
        self.folder_edit.setText(
            str(settings.value("convert/folder", ""))
        )
        into = str(settings.value("convert/into", "false")).lower()
        (self.into if into == "true" else self.beside).setChecked(True)

    # ---------------------------------------------------- run
    @property
    def busy(self) -> bool:
        """True while a run is in progress."""
        return self._thread is not None

    def _update_actions(self) -> None:
        busy = self.busy
        has_rows = self.table.rowCount() > 0
        folder_ok = not self.into.isChecked() or bool(
            self.folder_edit.text().strip()
        )
        ready = has_rows and bool(self.formats()) and folder_ok
        self.convert_btn.setEnabled(ready and not busy)
        self.stop_btn.setEnabled(busy)
        for w in (
            self.add_files_btn,
            self.add_folder_btn,
            self.clear_btn,
        ):
            w.setEnabled(not busy)
        self.remove_btn.setEnabled(
            not busy and bool(self.table.selectedIndexes())
        )
        if not self.formats():
            self.convert_btn.setToolTip("Choose at least one format")
        elif not folder_ok:
            self.convert_btn.setToolTip("Choose the output folder")
        else:
            self.convert_btn.setToolTip("Convert every source listed")

    def _set_status(
        self, row: int, text: str, state: str | None
    ) -> None:
        item = QTableWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, state)
        self._colour(item, state)
        self.table.setItem(row, _STATUS, item)

    def _log(self, text: str) -> None:
        self.log.appendPlainText(text)

    def start(self) -> bool:
        """Convert every source of the list in a worker thread.

        Returns
        -------
        bool
            False when nothing was started (empty list, no format,
            no output folder, or a run in progress).
        """
        if self.busy or not self.convert_btn.isEnabled():
            return False
        jobs = list(enumerate(self.sources()))
        self.results = []
        self._failed = 0
        options = self.options()
        target = options["out_dir"] or "next to each source"
        self._log(
            f"Converting {len(jobs)} source(s) to "
            f"{', '.join(options['formats'])}, {target}"
        )
        for row, _ in jobs:
            self._set_status(row, "waiting", None)
        self.progress.setRange(0, len(jobs))
        self.progress.setFormat("%v / %m")
        self.progress.setValue(0)
        thread = QThread(self)
        worker = _Worker(jobs, options)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.row_started.connect(self._row_started)
        worker.row_done.connect(self._row_done)
        worker.row_failed.connect(self._row_failed)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._finished)
        self._thread, self._worker = thread, worker
        self._update_actions()
        thread.start()
        return True

    def stop(self) -> None:
        """Stop after the source being converted."""
        if self._worker is not None:
            self._worker.stopped = True
            self._log("Stopping after the current source...")

    def wait(self, ms: int = 60000) -> bool:
        """Block until the run ends (for scripts and tests).

        Returns
        -------
        bool
            True when no run is left in progress.
        """
        from PySide6.QtCore import QCoreApplication, QDeadlineTimer

        deadline = QDeadlineTimer(ms)
        while self.busy and not deadline.hasExpired():
            QCoreApplication.processEvents()
            if self._thread is not None:
                self._thread.wait(20)
        QCoreApplication.processEvents()
        return not self.busy

    def _row_started(self, row: int) -> None:
        self._set_status(row, "converting...", None)
        self.table.scrollToItem(self.table.item(row, _SOURCE))

    def _row_done(self, row: int, result: ConversionResult) -> None:
        self.results.append(result)
        names = ", ".join(p.name for p in result.outputs)
        notes = []
        if result.conformance is False:
            notes.append(f"{len(result.failures)} rule(s) failed")
        if result.warnings:
            notes.append(f"{len(result.warnings)} reading note(s)")
        state = "warn" if notes else "done"
        text = f"{len(result.outputs)} file(s)"
        if notes:
            text += " - " + ", ".join(notes)
        self._set_status(row, text, state)
        self._log(
            f"OK    {result.source.name} ({result.kind} -> "
            f"{result.model_kind}, {result.seconds:.1f} s): {names}"
        )
        for line in result.failures:
            self._log(f"      rule {line}")
        for line in result.warnings:
            self._log(f"      note: {line}")
        self.progress.setValue(self.progress.value() + 1)

    def _row_failed(self, row: int, reason: str) -> None:
        self._failed += 1
        self._set_status(row, "failed", "failed")
        self.table.item(row, _STATUS).setToolTip(reason)
        name = self.sources()[row].name
        self._log(f"FAIL  {name}: {reason}")
        self.progress.setValue(self.progress.value() + 1)

    def _finished(self) -> None:
        thread, worker = self._thread, self._worker
        self._thread, self._worker = None, None
        if worker is not None:
            worker.deleteLater()
        if thread is not None:
            thread.deleteLater()
        done = len(self.results)
        summary = f"Converted {done} source(s)"
        if self._failed:
            summary += f", {self._failed} failed"
        self._log(summary)
        self._update_actions()
        self.message.emit(summary)
        self.run_done.emit(done)
        if self.open_box.isChecked() and self.results:
            self.open_requested.emit(self.results[0].outputs[0])
