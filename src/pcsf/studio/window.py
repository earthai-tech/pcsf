"""Qt widgets of PCSF Studio.

:class:`ModelView` shows one model and can be embedded in another Qt
application (pyCSAMT's desktop app uses it this way):

- a header card with the file name and status chips (geometry kind,
  solver, cells, stations, conformance, inversion record);
- the inspector (summary, stations, metadata, inversion record,
  conformance, reading notes) on the left;
- the plot with its controls in the centre;
- statistics of the whole model and of the current view, with a
  histogram of :math:`\\log_{10}\\rho`, on the right; the panel
  collapses to a thin strip (click its edge, or Ctrl+2) to give the
  plot more room.

:class:`StudioWindow` is the standalone application around it: a
toolbar (the logo at the far left, which leads to the start page;
open, samples, convert, save, export; the theme and the ``?`` help
menus at the far right), a start page with recent files, the
Convert page (:class:`~pcsf.studio.convert_page.ConvertPage`), which
writes solver runs as PCSF or PCSM in batches, and drag and drop.

The widgets only display what :mod:`pcsf.studio.figures` draws and
:mod:`pcsf.studio.summary` computes; they hold no format logic.

Notes
-----
Colours come from a :class:`~pcsf.studio.style.Theme` (light, dark,
or the one of the desktop). Panels whose content does not fit get
a scroll bar instead of being cut: the statistics panel and the
start page vertically, the header chips and the plot controls
horizontally. The window always opens centred on the screen, at
:data:`DEFAULT_SIZE` and at most :data:`SCREEN_SHARE` of its
available area; it remembers its theme and panel layout between
sessions.
"""

from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)
from matplotlib.figure import Figure
from PySide6.QtCore import (
    QByteArray,
    QEasingCurve,
    QPointF,
    QRect,
    QSettings,
    QSize,
    Qt,
    QUrl,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractButton,
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
    QScrollArea,
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
from .convert_page import ConvertPage
from .sources import LoadedModel, open_source
from .style import LIGHT, THEME_NAMES, Theme, get_theme, style_sheet

__all__ = [
    "ModelView",
    "StudioWindow",
    "application",
    "system_is_dark",
    "theme_palette",
]

logger = logging.getLogger(__name__)

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
#: Size (pixels) of the window when it opens, as pyCSAMT's desktop
#: application.
DEFAULT_SIZE = (1180, 700)
#: Largest share of the available screen the window opens with.
SCREEN_SHARE = 0.75
#: Height (pixels) kept free for a horizontal scroll bar.
_BAR = 12

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


def system_is_dark() -> bool:
    """Whether the desktop asks for a dark colour scheme.

    Returns
    -------
    bool
        True when Qt reports a dark scheme; False when it reports
        a light one, does not know, or is older than 6.5.
    """
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark
    except AttributeError:  # Qt < 6.5 has no colour scheme
        return False


def theme_palette(theme: Theme) -> QPalette:
    """Qt palette of a theme.

    The style sheet colours the widgets it names; the palette
    covers what the Qt style draws itself (check marks, spin box
    arrows) and tells matplotlib's toolbar which icons to use.

    Parameters
    ----------
    theme : Theme
        Colours to use.

    Returns
    -------
    QPalette
        Palette with the disabled text colours set as well.
    """
    role = QPalette.ColorRole
    pal = QPalette()
    for key, colour in (
        (role.Window, theme.back),
        (role.WindowText, theme.ink),
        (role.Base, theme.panel),
        (role.AlternateBase, theme.raised),
        (role.Text, theme.ink),
        (role.Button, theme.panel),
        (role.ButtonText, theme.ink),
        (role.ToolTipBase, theme.raised),
        (role.ToolTipText, theme.ink),
        (role.Highlight, theme.accent),
        (role.HighlightedText, theme.accent_ink),
        (role.PlaceholderText, theme.muted),
        (role.Link, theme.accent),
    ):
        pal.setColor(key, QColor(colour))
    for key in (role.WindowText, role.Text, role.ButtonText):
        pal.setColor(
            QPalette.ColorGroup.Disabled, key, QColor(theme.muted)
        )
    return pal


def _contrast_icon(colour: str, size: int = 18) -> QIcon:
    """Half-filled disc, the usual sign of a theme switch."""
    scale = 4  # drawn large and reduced by Qt, for smooth edges
    px = QPixmap(size * scale, size * scale)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(colour))
    pen.setWidthF(1.6 * scale)
    painter.setPen(pen)
    m = 2 * scale
    box = QRect(m, m, px.width() - 2 * m, px.height() - 2 * m)
    painter.drawEllipse(box)
    painter.setBrush(QColor(colour))
    # Qt angles are sixteenths of a degree, from three o'clock.
    painter.drawPie(box, 90 * 16, 180 * 16)
    painter.end()
    return QIcon(px)


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


def _rule() -> QFrame:
    line = QFrame()
    line.setObjectName("Rule")
    return line


def _scroll(
    widget: QWidget, mode: str = "vertical", height: int = 0
) -> QScrollArea:
    """Wrap *widget* so that a scroll bar appears when it is cut.

    Parameters
    ----------
    widget : QWidget
        Content; it keeps its minimum size and is stretched to the
        area when there is room.
    mode : {"vertical", "horizontal", "both"}
        ``"vertical"`` scrolls up and down, ``"horizontal"`` is a
        strip of fixed height that scrolls sideways, ``"both"`` a
        page that scrolls either way.
    height : int, default 0
        Height (pixels) of the content of a horizontal strip; its
        size hint when 0.

    Returns
    -------
    QScrollArea
        Frameless, transparent area holding *widget*.
    """
    area = QScrollArea()
    area.setObjectName("Scroll")
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    widget.setObjectName(widget.objectName() or "ScrollBody")
    area.setWidget(widget)
    off = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    if mode == "horizontal":
        area.setVerticalScrollBarPolicy(off)
        area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        # The bar gets its own room so that it never hides content.
        area.setFixedHeight(
            (height or widget.sizeHint().height()) + _BAR
        )
    elif mode == "vertical":
        area.setHorizontalScrollBarPolicy(off)
    return area


def _table(header: list[str], rows: list[list[Any]]) -> QTableWidget:
    t = QTableWidget(len(rows), len(header))
    t.setHorizontalHeaderLabels(header)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.setShowGrid(False)
    # Scroll by pixel: rows of wrapped text would jump otherwise.
    t.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
    t.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            text = (
                f"{value:.6g}"
                if isinstance(value, float)
                else str(value)
            )
            item = QTableWidgetItem(text)
            item.setToolTip(text)
            t.setItem(i, j, item)
    t.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.ResizeToContents
    )
    t.horizontalHeader().setStretchLastSection(True)
    return t


def _fill_tree(parent: Any, value: Any) -> None:
    for key, sub in value.items():
        if isinstance(sub, dict):
            item = QTreeWidgetItem(parent, [str(key), ""])
            _fill_tree(item, sub)
        else:
            item = QTreeWidgetItem(parent, [str(key), str(sub)])
            item.setToolTip(1, str(sub))


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


def _explain(exc: BaseException) -> str:
    """One sentence a user can act on, for an error dialog."""
    if isinstance(exc, FileNotFoundError):
        return (
            "The file or folder does not exist. It may have been "
            "moved, renamed, or be on a drive that is not connected."
        )
    if isinstance(exc, PermissionError):
        return (
            "Access was denied. The file may be open in another "
            "program, or the folder may be read-only."
        )
    if isinstance(exc, MemoryError):
        return "There is not enough memory for this model."
    text = str(exc).strip() or "no message"
    return f"{type(exc).__name__}: {text}"


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
    """Statistics of the model and of the current view.

    The tiles and the histogram sit in a scroll area, so a short
    window scrolls them instead of squeezing them.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumWidth(250)
        self.setMaximumWidth(340)
        self.theme = LIGHT
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 4, 0)
        lay.setSpacing(6)
        lay.addWidget(_label("Whole model", "Muted"))
        self.model_block = _StatsBlock()
        lay.addWidget(self.model_block)
        lay.addSpacing(4)
        self.view_title = _label("Current view", "Muted", wrap=True)
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
        card, card_lay = _card()
        card_lay.addWidget(_label("STATISTICS", "Section"))
        card_lay.addWidget(_scroll(body), 1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
        self._model_logs = np.array([])
        self._view: tuple[np.ndarray, float, float] | None = None

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._draw_hist()

    def set_model(self, model: Any) -> None:
        values = figures._model_values(model)
        self.model_block.show_stats(summary.value_stats(values))
        self._model_logs = _earth_logs(values)

    def set_view(
        self, label: str, values: np.ndarray, vmin: float, vmax: float
    ) -> None:
        self.view_title.setText(f"Current view: {label}")
        self.view_block.show_stats(summary.value_stats(values))
        self._view = (_earth_logs(values), vmin, vmax)
        self._draw_hist()

    def _draw_hist(self) -> None:
        theme = self.theme
        fig = self.hist_fig
        fig.clear()
        ax = fig.add_subplot(1, 1, 1)
        if self._view is None:
            view_logs, limits = np.array([]), ()
        else:
            view_logs, limits = self._view[0], self._view[1:]
        both = np.concatenate([self._model_logs, view_logs])
        if both.size:
            bins = np.linspace(both.min(), both.max() + 1e-9, 31)
            ax.hist(
                self._model_logs,
                bins=bins,
                color=theme.hist,
                label="model",
                density=True,
            )
            if view_logs.size:
                ax.hist(
                    view_logs,
                    bins=bins,
                    color=theme.accent,
                    alpha=0.75,
                    label="view",
                    density=True,
                )
            for v in limits:
                ax.axvline(v, color=theme.ink, lw=0.8, ls="--")
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
        figures.restyle(
            fig,
            ink=theme.ink,
            background=theme.panel,
            muted=theme.muted,
        )
        self.hist.draw_idle()


class _EdgeButton(QAbstractButton):
    """Thin, full-height button on the left edge of a side panel.

    It shows a chevron pointing where the panel will go when
    clicked: right (collapse) while the panel is open, left
    (expand) while it is collapsed, when the label of the panel
    is also written vertically, so the strip says what it holds.
    """

    WIDTH = 18

    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label
        self.collapsed = False
        self.theme = LIGHT
        self.setFixedWidth(self.WIDTH)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def sizeHint(self) -> QSize:
        return QSize(self.WIDTH, 120)

    def set_collapsed(self, collapsed: bool) -> None:
        self.collapsed = collapsed
        what = "Show" if collapsed else "Hide"
        self.setToolTip(f"{what} the {self.label.lower()} (Ctrl+2)")
        self.update()

    def paintEvent(self, _: Any) -> None:
        t = self.theme
        hot = self.underMouse()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = self.rect().adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(t.line)))
        p.setBrush(QColor(t.accent_soft if hot else t.panel))
        p.drawRoundedRect(box, 6, 6)
        pen = QPen(QColor(t.accent if hot else t.muted), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        cx, cy = box.center().x() + 0.5, 22.0
        # ">" when the panel is open (it goes right), "<" otherwise
        d = -3.0 if self.collapsed else 3.0
        p.drawLine(QPointF(cx - d, cy - 5), QPointF(cx + d, cy))
        p.drawLine(QPointF(cx + d, cy), QPointF(cx - d, cy + 5))
        if self.collapsed:
            font = QFont(self.font())
            font.setPointSizeF(7.5)
            font.setBold(True)
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
            p.setFont(font)
            p.setPen(QColor(t.accent if hot else t.muted))
            # Turned a quarter clockwise, the glyphs stand to the
            # right of the baseline: centre their height on the strip.
            metrics = QFontMetrics(font)
            x = box.center().x() + 0.5 - metrics.ascent() / 2
            x += metrics.descent() / 2
            p.translate(x, 40)
            p.rotate(90)
            p.drawText(0, 0, self.label.upper())
        p.end()


class _SidePanel(QWidget):
    """A panel that collapses to a thin strip on the right.

    Parameters
    ----------
    panel : QWidget
        The panel; it is hidden while collapsed.
    label : str
        Name of the panel, written on the collapsed strip.

    Notes
    -----
    Signal ``toggled(bool)`` is emitted with the new state (True
    when expanded) after :meth:`set_expanded` changes it. In a
    :class:`QSplitter`, the width freed by collapsing goes to the
    stretching neighbours, and expanding gives back the width the
    panel had, with a short slide when *animate* is True.
    """

    toggled = Signal(bool)
    #: Duration (ms) of the slide.
    DURATION = 180

    def __init__(self, panel: QWidget, label: str) -> None:
        super().__init__()
        self.panel = panel
        self.edge = _EdgeButton(label)
        self.expanded = True
        self._width = 300
        self._anim: QVariantAnimation | None = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self.edge)
        lay.addWidget(panel, 1)
        self.edge.clicked.connect(self.toggle)
        self.edge.set_collapsed(False)
        self._limits = (panel.minimumWidth(), panel.maximumWidth())
        self._relax()

    def set_theme(self, theme: Theme) -> None:
        self.edge.theme = theme
        self.edge.update()

    def toggle(self) -> None:
        """Collapse an expanded panel, expand a collapsed one."""
        self.set_expanded(not self.expanded)

    def _strip(self) -> int:
        return self.edge.WIDTH + 2

    def _relax(self) -> None:
        """Width limits of the expanded panel."""
        lo, hi = self._limits
        gap = self.layout().spacing() + self.edge.WIDTH
        self.panel.setMinimumWidth(lo)
        self.setMinimumWidth(lo + gap)
        self.setMaximumWidth(hi + gap)

    def set_expanded(
        self, expanded: bool, animate: bool = True
    ) -> None:
        """Expand or collapse the panel.

        Parameters
        ----------
        expanded : bool
            True to show the panel, False to keep only the strip.
        animate : bool, default True
            Slide instead of jumping; ignored while the widget is
            not visible.
        """
        expanded = bool(expanded)
        if expanded == self.expanded:
            return
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        self.expanded = expanded
        self.edge.set_collapsed(not expanded)
        start = self.width()
        if not expanded:
            self._width = max(start, self.minimumWidth())
        end = self._width if expanded else self._strip()
        # the panel may be narrower than its minimum while sliding
        self.panel.setMinimumWidth(0)
        self.setMinimumWidth(0)
        if expanded:
            self.panel.show()
        if animate and self.isVisible():
            anim = QVariantAnimation(self)
            anim.setDuration(self.DURATION)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setStartValue(start)
            anim.setEndValue(end)
            anim.valueChanged.connect(
                lambda w: self._set_width(int(w))
            )
            anim.finished.connect(self._settle)
            self._anim = anim
            anim.start()
        else:
            self._set_width(end)
            self._settle()
        self.toggled.emit(expanded)

    def _set_width(self, width: int) -> None:
        """Take *width* and give the difference to the neighbours.

        In a splitter the width freed (or taken) goes to the widget
        on the left, the plot, so the others keep their size.
        """
        self.setFixedWidth(width)
        split = self.parentWidget()
        if not isinstance(split, QSplitter):
            return
        sizes = split.sizes()
        i = split.indexOf(self)
        if i < 1 or not any(sizes):
            return
        sizes[i - 1] += sizes[i] - width
        sizes[i] = width
        split.setSizes(sizes)

    def _settle(self) -> None:
        self._anim = None
        if self.expanded:
            width = self.width()
            self._relax()
            self._set_width(width)
            self._relax()
        else:
            self.panel.hide()
            self._set_width(self._strip())


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
    stats : QWidget
        Statistics panel.
    stats_side : QWidget
        The statistics panel with the strip that collapses it to
        the right (``stats_side.set_expanded(False)``), which gives
        its width to the plot.
    split : QSplitter
        Holds the inspector, the plot and the statistics.
    theme : Theme
        Colours in use, set by :meth:`set_theme`.

    Notes
    -----
    Signal ``model_changed(object)`` is emitted with the
    :class:`~pcsf.studio.sources.LoadedModel` after each
    :meth:`set_model`. Signal ``plot_failed(str)`` is emitted with
    a message when a view cannot be drawn; the message is also
    written on the plot, so the application keeps running.

    Examples
    --------
    Embedding in another application::

        from pcsf.studio import ModelView
        from pcsf.studio.sources import open_source
        from pcsf.studio.style import DARK, style_sheet

        view = ModelView()
        view.setStyleSheet(style_sheet(DARK))
        view.set_theme(DARK)
        view.set_model(open_source("model.pcsf"))
        layout.addWidget(view)
    """

    model_changed = Signal(object)
    plot_failed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Page")
        self.loaded: LoadedModel | None = None
        self.theme: Theme = LIGHT
        self.figure = Figure(figsize=(7, 5), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.canvas.setMinimumSize(260, 200)
        self.tabs = QTabWidget()
        self.stats = _StatsPanel()
        self.stats_side = _SidePanel(self.stats, "Statistics")
        # the plot fills the width freed by the panel at once
        self.stats_side.toggled.connect(
            lambda _: self.canvas.draw_idle()
        )
        self._build()

    # ------------------------------------------------- layout
    def _header(self) -> QFrame:
        card, lay = _card()
        self.title = _label("", "Title")
        self.subtitle = _label("", "Subtitle")
        self.subtitle.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        for lab in (self.title, self.subtitle):
            # A long name or path must not widen the window; the
            # full text is in the tool tip.
            lab.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Preferred,
            )
            lay.addWidget(lab)
        strip = QWidget()
        self.chips = QHBoxLayout(strip)
        self.chips.setContentsMargins(0, 0, 0, 0)
        self.chips.setSpacing(6)
        lay.addWidget(_scroll(strip, "horizontal", height=24))
        return card

    def _controls(self) -> QWidget:
        self.view_box = QComboBox()
        self.view_box.setMinimumWidth(110)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimumWidth(120)
        self.slider.setToolTip(
            "Position of the slice, section or line "
            "(arrow keys step by one)"
        )
        self.position = _label("", "Muted")
        self.position.setMinimumWidth(110)
        self.cmap_box = QComboBox()
        self.cmap_box.addItems(CMAPS)
        self.auto_range = QCheckBox("Auto")
        self.auto_range.setChecked(True)
        self.auto_range.setToolTip(
            "Colour range from the 2nd to the 98th percentile of "
            "the model"
        )
        self.vmin = QDoubleSpinBox()
        self.vmax = QDoubleSpinBox()
        for box in (self.vmin, self.vmax):
            box.setRange(-10.0, 20.0)
            box.setDecimals(2)
            box.setSingleStep(0.1)
            box.setEnabled(False)
            box.setMinimumWidth(70)
        self.depth = QDoubleSpinBox()
        self.depth.setRange(0.0, 1e7)
        self.depth.setDecimals(0)
        self.depth.setSingleStep(100.0)
        self.depth.setSpecialValueText("whole model")
        self.depth.setSuffix(" m")
        self.depth.setMinimumWidth(105)
        self.depth.setToolTip("Largest depth shown on sections")
        self.stations_box = QCheckBox("Stations")
        self.stations_box.setChecked(True)
        self.fit_box = QCheckBox("Fit to survey")
        self.fit_box.setToolTip(
            "Limit the horizontal axes to the station extent"
        )

        box = QWidget()
        grid = QGridLayout(box)
        grid.setContentsMargins(0, 2, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(_label("View", "Muted"), 0, 0)
        grid.addWidget(self.view_box, 0, 1)
        grid.addWidget(_label("Position", "Muted"), 0, 2)
        pos = QHBoxLayout()
        pos.addWidget(self.slider, 1)
        pos.addWidget(self.position)
        grid.addLayout(pos, 0, 3)
        grid.addWidget(_label("Colours", "Muted"), 1, 0)
        grid.addWidget(self.cmap_box, 1, 1)
        grid.addWidget(_label(LOG10_RHO, "Muted"), 1, 2)
        rng = QHBoxLayout()
        rng.setSpacing(8)
        rng.addWidget(self.auto_range)
        rng.addWidget(self.vmin)
        rng.addWidget(_label("to", "Muted"))
        rng.addWidget(self.vmax)
        rng.addStretch(1)
        grid.addLayout(rng, 1, 3)
        grid.addWidget(_label("Depth", "Muted"), 2, 0)
        grid.addWidget(self.depth, 2, 1)
        grid.addWidget(_label("Show", "Muted"), 2, 2)
        opts = QHBoxLayout()
        opts.setSpacing(12)
        opts.addWidget(self.stations_box)
        opts.addWidget(self.fit_box)
        opts.addStretch(1)
        grid.addLayout(opts, 2, 3)
        grid.setColumnStretch(3, 1)
        return _scroll(box, "horizontal")

    def _nav(self) -> NavigationToolbar2QT:
        nav = NavigationToolbar2QT(self.canvas, self)
        nav.setObjectName("PlotBar")
        nav.setIconSize(QSize(18, 18))
        return nav

    def _build(self) -> None:
        plot_card, self._plot_lay = _card()
        self.nav = self._nav()
        self._plot_lay.addWidget(self.nav)
        self._plot_lay.addWidget(self.canvas, 1)
        self._plot_lay.addWidget(_rule())
        self._plot_lay.addWidget(self._controls())

        self.tabs.setMinimumWidth(240)
        self.tabs.setUsesScrollButtons(True)
        self.split = QSplitter()
        self.split.setChildrenCollapsible(False)
        self.split.addWidget(self.tabs)
        self.split.addWidget(plot_card)
        self.split.addWidget(self.stats_side)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 1)
        self.split.setStretchFactor(2, 0)
        self.split.setSizes([300, 640, 300])

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)
        lay.addWidget(self._header())
        lay.addWidget(self.split, 1)

        self.view_box.currentTextChanged.connect(self._view_changed)
        self.slider.valueChanged.connect(self.redraw)
        self.cmap_box.currentTextChanged.connect(self.redraw)
        self.auto_range.toggled.connect(self._range_toggled)
        self.vmin.valueChanged.connect(self.redraw)
        self.vmax.valueChanged.connect(self.redraw)
        self.stations_box.toggled.connect(self.redraw)
        self.fit_box.toggled.connect(self.redraw)
        self.depth.valueChanged.connect(self.redraw)
        self._paint_empty()

    # -------------------------------------------------- theme
    def set_theme(self, theme: Theme) -> None:
        """Use the colours of a theme for the plots.

        The widget palette is set, the matplotlib toolbar is built
        again (its icons depend on the background) and the plot
        and the histogram are redrawn. The style sheet is not
        touched: set :func:`~pcsf.studio.style.style_sheet` on
        this widget or on its window.

        Parameters
        ----------
        theme : Theme
            :data:`~pcsf.studio.style.LIGHT` or
            :data:`~pcsf.studio.style.DARK`.
        """
        self.theme = theme
        self.setPalette(theme_palette(theme))
        old, self.nav = self.nav, self._nav()
        self._plot_lay.replaceWidget(old, self.nav)
        old.hide()
        old.deleteLater()
        self.stats.set_theme(theme)
        self.stats_side.set_theme(theme)
        if self.loaded is None:
            self._paint_empty()
        else:
            self.redraw()

    def _restyle(self, theme: Theme | None = None) -> None:
        theme = theme or self.theme
        figures.restyle(
            self.figure,
            ink=theme.ink,
            background=theme.panel,
            muted=theme.muted,
        )

    def _paint_empty(self) -> None:
        self.figure.clear()
        self._restyle()
        self.canvas.draw_idle()

    def save_figure(self, path: Any, dpi: int = 200) -> None:
        """Save the plot as it would print, on a white background.

        Parameters
        ----------
        path : path-like
            Target; the suffix gives the format (PNG, SVG, PDF...).
        dpi : int, default 200
            Resolution of raster formats, in dots per inch.

        Raises
        ------
        OSError
            If the file cannot be written.
        ValueError
            If matplotlib does not know the format.

        Notes
        -----
        The figure is recoloured with the light theme for the
        file and back to the current theme afterwards, so a dark
        screen does not give a dark figure.
        """
        self._restyle(LIGHT)
        try:
            self.figure.savefig(path, dpi=dpi)
        finally:
            self._restyle()
            self.canvas.draw_idle()

    # -------------------------------------------------- model
    def set_model(self, loaded: LoadedModel) -> None:
        """Show a model.

        Parameters
        ----------
        loaded : LoadedModel
            Result of :func:`~pcsf.studio.sources.open_source`.

        Raises
        ------
        Exception
            Whatever the inspector raised on a malformed model.
            The model shown before, if any, is shown again, so the
            view never mixes two models.
        """
        previous = self.loaded
        try:
            self._show(loaded)
        except Exception:
            if previous is not None:
                self._show(previous)
            else:
                self.loaded = None
            raise
        self.model_changed.emit(loaded)

    def _show(self, loaded: LoadedModel) -> None:
        model = loaded.model
        self._fill_header(loaded)
        self._fill_tabs(loaded)
        self.stats.set_model(model)
        lo, hi = figures.color_range(model)
        self.loaded = loaded
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
        self.title.setToolTip(str(loaded.path))
        desc = model.description or "no description"
        self.subtitle.setText(f"{loaded.path.parent}  •  {desc}")
        self.subtitle.setToolTip(f"{loaded.path.parent}\n{desc}")
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
        current = self.tabs.tabText(self.tabs.currentIndex())
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
        tree.setAlternatingRowColors(True)
        _fill_tree(
            tree.invisibleRootItem(), summary.metadata_tree(model)
        )
        tree.expandToDepth(0)
        tree.resizeColumnToContents(0)
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
        # Keep the tab the user was reading across models.
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == current:
                self.tabs.setCurrentIndex(i)
                break

    # --------------------------------------------------- plot
    def _view_changed(self, view: str) -> None:
        if self.loaded is None or not view:
            return
        try:
            n = figures.n_positions(self.loaded.model, view)
        except Exception as exc:  # reported on the plot
            self._plot_error(exc)
            return
        n = max(int(n), 1)
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

    def _plot_error(self, exc: BaseException) -> None:
        """Write a drawing error on the plot instead of raising."""
        logger.warning("cannot draw the view", exc_info=exc)
        message = f"Cannot draw this view. {_explain(exc)}"
        self.figure.clear()
        self.figure.text(
            0.5, 0.5, message, ha="center", va="center", wrap=True
        )
        self._restyle()
        self.canvas.draw_idle()
        self.plot_failed.emit(message)

    def redraw(self, *_: Any) -> None:
        """Draw the current view and update its statistics.

        A view that cannot be drawn (malformed geometry, values
        matplotlib rejects) does not raise: the reason is written
        on the plot and sent with ``plot_failed``.
        """
        if self.loaded is None or not self.view_box.currentText():
            return
        model = self.loaded.model
        view = self.view_box.currentText()
        index = self.slider.value()
        if self.auto_range.isChecked():
            vmin, vmax = figures.color_range(model)
        else:
            vmin, vmax = self.vmin.value(), self.vmax.value()
            if vmax <= vmin:
                # An empty or reversed range has no colours; keep
                # the lower limit the user is typing.
                vmax = vmin + self.vmax.singleStep()
        try:
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
            values = figures.view_values(model, view, index)
        except Exception as exc:  # reported on the plot
            self._plot_error(exc)
            return
        self._restyle()
        self.position.setText(label)
        self.stats.set_view(
            f"{view}{', ' + label if label else ''}",
            values,
            vmin,
            vmax,
        )
        self.canvas.draw_idle()


# -------------------------------------------------------- welcome page
class _Welcome(QWidget):
    """Start page: logo, actions, samples and recent files."""

    def __init__(self, window: StudioWindow) -> None:
        super().__init__()
        self.setObjectName("Page")
        card, lay = _card()
        card.setFixedWidth(660)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(8)
        logo = QLabel()
        logo.setPixmap(logo_icon().pixmap(QSize(84, 84)))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)
        title = _label("PCSF Studio", "Hero")
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
        lay.addSpacing(10)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch(1)
        open_btn = QPushButton("Open file...")
        open_btn.setObjectName("Primary")
        open_btn.clicked.connect(window.open_file)
        folder_btn = QPushButton("Open run folder...")
        folder_btn.clicked.connect(window.open_folder)
        convert_btn = QPushButton("Convert runs...")
        convert_btn.setToolTip(
            "Convert Occam2D, ModEM, MARE2DEM or EMC output to "
            "PCSF or PCSM"
        )
        convert_btn.clicked.connect(window.show_convert)
        sample_btn = QPushButton("Try a sample")
        sample_btn.setMenu(window.samples_menu)
        for b in (open_btn, folder_btn, convert_btn, sample_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addSpacing(12)
        lay.addWidget(_rule())
        lay.addSpacing(4)
        lay.addWidget(_label("RECENT", "Section"))
        self.recent = QListWidget()
        self.recent.setObjectName("Recent")
        self.recent.setMinimumHeight(96)
        self.recent.setMaximumHeight(210)
        self.recent.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.recent.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.recent.setUniformItemSizes(True)
        self.recent.itemActivated.connect(self._activated)
        self._window = window
        lay.addWidget(self.recent)
        hint = _label(
            "Or drop a file or a run folder on this window.", "Muted"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        ver = _label(f"pcsf {__version__}", "Muted")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ver)

        # The card is centred in a page that scrolls when the
        # window is smaller than the card.
        page = QWidget()
        grid = QGridLayout(page)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(2, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(2, 1)
        grid.addWidget(card, 1, 1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll(page, "both"))

    def _activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:  # the "no recent files" line carries no path
            self._window.open(path)

    def set_recent(self, paths: list[str]) -> None:
        self.recent.clear()
        for p in paths:
            item = QListWidgetItem(f"{Path(p).name}\n{Path(p).parent}")
            item.setToolTip(p)
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.recent.addItem(item)
        if not paths:
            item = QListWidgetItem("No recent files")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.recent.addItem(item)


# ------------------------------------------------------- main window
class StudioWindow(QMainWindow):
    """Main window of PCSF Studio.

    Parameters
    ----------
    path : path-like, optional
        File or run folder opened at start.
    settings : QSettings, optional
        Where the recent files, the theme, the window size and the
        panel layout are kept; the user settings of
        ``earthai-tech/PCSF Studio`` by default.
    theme : {"system", "light", "dark"}, optional
        Theme to start with; the one kept in *settings* by
        default, ``"system"`` when there is none.

    Attributes
    ----------
    view : ModelView
        The model page.
    theme_name : str
        Theme chosen, one of
        :data:`~pcsf.studio.style.THEME_NAMES`.
    theme : Theme
        Colours in use (``"system"`` resolved).

    Raises
    ------
    ValueError
        If *theme* is not a theme name.
    """

    def __init__(
        self,
        path: Any = None,
        settings: QSettings | None = None,
        theme: str | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("PCSF Studio")
        self.setWindowIcon(logo_icon())
        self.setAcceptDrops(True)
        self.settings = settings or QSettings(
            "earthai-tech", "PCSF Studio"
        )
        self.theme_name = "system"
        self.theme: Theme = LIGHT
        self.samples_menu = self._samples_menu()
        self.view = ModelView()
        self.view.plot_failed.connect(self._status)
        self.convert = ConvertPage()
        self.convert.start_folder = self._last_folder
        self.convert.open_requested.connect(self.open)
        self.convert.message.connect(self._status)
        self.welcome = _Welcome(self)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.welcome)
        self.pages.addWidget(self.view)
        self.pages.addWidget(self.convert)
        self.setCentralWidget(self.pages)
        self._toolbar()
        self._menus()
        self._refresh_recent()
        self.statusBar().addPermanentWidget(
            _label(f"pcsf {__version__}", "Muted")
        )
        self._status("Ready")
        if theme is None:
            theme = str(self.settings.value("theme", "system"))
            if theme.lower() not in THEME_NAMES:
                theme = "system"
        self.set_theme(theme, remember=False)
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(self._system_changed)
        self._restore_layout()
        if path is not None:
            self.open(path)

    # ------------------------------------------------- layout
    def _screen_area(self) -> QRect | None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        return None if screen is None else screen.availableGeometry()

    def place_default(self) -> None:
        """Give the window its default size, centred on the screen.

        The size is :data:`DEFAULT_SIZE`, reduced to
        :data:`SCREEN_SHARE` of the available screen (without the
        task bar) when the screen is smaller, so the window never
        covers the whole desktop. A maximized or full-screen
        window is brought back to a normal one first.
        """
        self.setWindowState(Qt.WindowState.WindowNoState)
        area = self._screen_area()
        if area is None:  # no screen (some offscreen platforms)
            self.resize(*DEFAULT_SIZE)
            return
        w = min(DEFAULT_SIZE[0], int(area.width() * SCREEN_SHARE))
        h = min(DEFAULT_SIZE[1], int(area.height() * SCREEN_SHARE))
        self.setGeometry(
            area.x() + (area.width() - w) // 2,
            area.y() + (area.height() - h) // 2,
            w,
            h,
        )

    def _restore_layout(self) -> None:
        # The window always opens at its default size, centred: a
        # size kept from an earlier session (possibly maximized, or
        # on another screen) would make it cover the desktop. Only
        # the panel layout is restored.
        self.place_default()
        s = self.settings
        s.remove("geometry")  # size kept by earlier versions
        self.convert.load_settings(s)
        split = s.value("split")
        if isinstance(split, QByteArray) and not split.isEmpty():
            self.view.split.restoreState(split)
        for key, act in (
            ("inspector", self.inspector_act),
            ("statistics", self.stats_act),
        ):
            shown = str(s.value(key, "true")).lower() != "false"
            act.setChecked(shown)

    def closeEvent(self, event: Any) -> None:
        if self.convert.busy:  # finish the file being written
            self.convert.stop()
            self.convert.wait()
        s = self.settings
        s.setValue("split", self.view.split.saveState())
        self.convert.save_settings(s)
        s.setValue("inspector", self.inspector_act.isChecked())
        s.setValue("statistics", self.stats_act.isChecked())
        super().closeEvent(event)

    def _status(self, text: str) -> None:
        self.statusBar().showMessage(text)

    # -------------------------------------------------- theme
    def set_theme(self, name: str, remember: bool = True) -> None:
        """Switch the theme of the window.

        Parameters
        ----------
        name : {"system", "light", "dark"}
            ``"system"`` follows the colour scheme of the desktop,
            also when it changes while the window is open.
        remember : bool, default True
            Keep the choice in the settings for the next session.

        Raises
        ------
        ValueError
            If *name* is not a theme name.

        Notes
        -----
        The palette of the application is set as well, so that
        dialogs and menus follow. The window is meant to be the
        only one of its application; embed :class:`ModelView` to
        leave the palette of a host application alone.
        """
        theme = get_theme(name, system_is_dark())
        self.theme_name = str(name).lower()
        self.theme = theme
        app = QApplication.instance()
        if app is not None:
            app.setPalette(theme_palette(theme))
        self.setStyleSheet(style_sheet(theme))
        self.view.set_theme(theme)
        self.convert.set_theme(theme)
        self.theme_button.setIcon(_contrast_icon(theme.ink))
        self.theme_actions[self.theme_name].setChecked(True)
        if remember:
            self.settings.setValue("theme", self.theme_name)

    def toggle_theme(self) -> None:
        """Switch between the light and the dark theme."""
        self.set_theme("light" if self.theme.dark else "dark")

    def _system_changed(self, *_: Any) -> None:
        if self.theme_name == "system":
            self.set_theme("system", remember=False)

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

    def _menu_button(
        self, text: str, menu: QMenu, name: str = ""
    ) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        if name:
            button.setObjectName(name)
        button.setMenu(menu)
        button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        return button

    def _toolbar(self) -> None:
        bar = QToolBar("Main")
        bar.setObjectName("MainBar")
        bar.setMovable(False)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        # Without this, a right click offers to hide the toolbar.
        bar.setContextMenuPolicy(
            Qt.ContextMenuPolicy.PreventContextMenu
        )
        self.addToolBar(bar)

        # Far left: the logo, which leads to the start page.
        self.home_act = self._action(
            "Start page",
            self.show_welcome,
            "Ctrl+Home",
            tip="Back to the start page (Ctrl+Home)",
        )
        brand = QToolButton()
        brand.setObjectName("Brand")
        brand.setIcon(logo_icon())
        brand.setIconSize(QSize(24, 24))
        brand.setText(" PCSF Studio")
        brand.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        brand.setToolTip(self.home_act.toolTip())
        brand.clicked.connect(self.show_welcome)
        self.brand_button = brand
        bar.addWidget(brand)
        bar.addSeparator()

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
        bar.addWidget(self._menu_button("Samples", self.samples_menu))
        bar.addSeparator()
        self.convert_act = self._action(
            "Convert",
            self.show_convert,
            "Ctrl+Shift+C",
            tip=(
                "Convert solver runs to PCSF, PCSM or PCSM gzip "
                "(Ctrl+Shift+C)"
            ),
        )
        bar.addAction(self.convert_act)
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
        self.export_button = self._menu_button(
            "Export", self.export_menu
        )
        self.export_button.setEnabled(False)
        bar.addWidget(self.export_button)
        self.reload_act = self._action(
            "Reload",
            self.reload,
            "F5",
            False,
            "Read the model again from disk (F5)",
        )
        bar.addAction(self.reload_act)

        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        bar.addWidget(spacer)

        # Far right: theme, then help behind a plain "?".
        self.theme_menu = QMenu("Theme", self)
        group = QActionGroup(self)
        self.theme_actions: dict[str, QAction] = {}
        for name, text in (
            ("system", "Follow the system"),
            ("light", "Light"),
            ("dark", "Dark"),
        ):
            act = self._action(
                text, lambda _=False, n=name: self.set_theme(n)
            )
            act.setCheckable(True)
            group.addAction(act)
            self.theme_actions[name] = act
            self.theme_menu.addAction(act)
        self.theme_menu.addSeparator()
        self.theme_menu.addAction(
            self._action(
                "Switch light / dark", self.toggle_theme, "Ctrl+T"
            )
        )
        self.theme_button = self._menu_button(
            "", self.theme_menu, "Round"
        )
        self.theme_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        self.theme_button.setIconSize(QSize(18, 18))
        self.theme_button.setToolTip("Theme: light, dark or system")
        bar.addWidget(self.theme_button)

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
        self.help_button = self._menu_button(
            "?", self.help_menu, "Round"
        )
        self.help_button.setToolTip("Help and about PCSF Studio")
        bar.addWidget(self.help_button)
        self._model_actions = [
            self.save_act,
            self.fig_act,
            self.cells_act,
            self.stations_act,
            self.reload_act,
        ]

    def _menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        for act in (self.open_act, self.folder_act):
            file_menu.addAction(act)
        file_menu.addMenu(self.samples_menu)
        file_menu.addAction(self.convert_act)
        self.recent_menu = file_menu.addMenu("Recent")
        file_menu.addAction(self.reload_act)
        file_menu.addSeparator()
        file_menu.addAction(self.save_act)
        file_menu.addMenu(self.export_menu)
        file_menu.addSeparator()
        file_menu.addAction(
            self._action(
                "Quit", self.close, QKeySequence.StandardKey.Quit
            )
        )

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.home_act)
        view_menu.addSeparator()
        self.inspector_act = QAction("Inspector", self)
        self.stats_act = QAction("Statistics", self)
        for act, key in (
            (self.inspector_act, "Ctrl+1"),
            (self.stats_act, "Ctrl+2"),
        ):
            act.setShortcut(QKeySequence(key))
            act.setCheckable(True)
            act.setChecked(True)
            view_menu.addAction(act)
        # toggled, not triggered: it also fires when the layout of
        # the last session is restored
        self.inspector_act.toggled.connect(self.view.tabs.setVisible)
        side = self.view.stats_side
        self.stats_act.toggled.connect(side.set_expanded)
        # the strip of the panel and the menu stay in step
        side.toggled.connect(self.stats_act.setChecked)
        view_menu.addSeparator()
        view_menu.addMenu(self.theme_menu)
        view_menu.addAction(
            self._action("Reset window size", self.place_default)
        )
        self.menuBar().addMenu(self.help_menu)

    # ------------------------------------------------- recent
    def _recent(self) -> list[str]:
        value = self.settings.value("recent", [])
        if isinstance(value, str):
            value = [value]
        return [p for p in (value or []) if p and Path(p).exists()]

    def _remember(self, path: Path) -> None:
        items = [str(path)] + [
            p for p in self._recent() if p != str(path)
        ]
        self.settings.setValue("recent", items[:MAX_RECENT])
        self._refresh_recent()

    def clear_recent(self) -> None:
        """Forget the recent files."""
        self.settings.setValue("recent", [])
        self._refresh_recent()

    def _refresh_recent(self) -> None:
        recent = self._recent()
        self.welcome.set_recent(recent)
        self.recent_menu.clear()
        for p in recent:
            act = QAction(p, self)
            act.triggered.connect(lambda _=False, q=p: self.open(q))
            self.recent_menu.addAction(act)
        if recent:
            self.recent_menu.addSeparator()
            self.recent_menu.addAction(
                self._action("Clear the list", self.clear_recent)
            )
        self.recent_menu.setEnabled(bool(recent))

    # --------------------------------------------------- open
    def _fail(
        self, title: str, subject: str, exc: BaseException
    ) -> None:
        """Show an error: what failed, why, and the traceback."""
        logger.warning("%s: %s", title, subject, exc_info=exc)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle(title)
        box.setText(subject)
        box.setInformativeText(_explain(exc))
        box.setDetailedText(
            "".join(
                traceback.format_exception(
                    type(exc), exc, exc.__traceback__
                )
            )
        )
        box.exec()

    def open(self, path: Any) -> bool:
        """Open a file or run folder and show it.

        Parameters
        ----------
        path : path-like
            Passed to :func:`~pcsf.studio.sources.open_source`.

        Returns
        -------
        bool
            True when the model was opened. On failure a dialog
            gives the reason (with the traceback under "Show
            details"), the model shown before stays, and False is
            returned; an empty *path* returns False silently.
        """
        if path is None or not str(path):
            return False
        error: Exception | None = None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self._status(f"Opening {path} ...")
        try:
            loaded = open_source(path)
            self.view.set_model(loaded)
        except Exception as exc:  # shown to the user, not hidden
            error = exc
        finally:
            QApplication.restoreOverrideCursor()
        if error is not None:
            self._status("Cannot open the file")
            self._fail("Cannot open", Path(path).name, error)
            # A recent file that vanished leaves the lists.
            self._refresh_recent()
            return False
        self.pages.setCurrentWidget(self.view)
        self.setWindowTitle(f"{loaded.title} - PCSF Studio")
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
        self._status(
            f"{loaded.path}   {loaded.kind} → {loaded.model.kind}"
            f"{note}"
        )
        return True

    def reload(self) -> None:
        """Read the model shown again from disk."""
        if self.view.loaded is not None:
            self.open(self.view.loaded.path)

    def open_file(self) -> None:
        """Ask for a file and open it."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open file", self._last_folder(), _OPEN_FILTER
        )
        if path:
            self.open(path)

    def open_folder(self) -> None:
        """Ask for a run folder and open it."""
        path = QFileDialog.getExistingDirectory(
            self, "Open run folder", self._last_folder()
        )
        if path:
            self.open(path)

    def _last_folder(self) -> str:
        """Folder of the most recent file, to start dialogs in."""
        recent = self._recent()
        return str(Path(recent[0]).parent) if recent else ""

    def show_welcome(self) -> None:
        """Show the start page."""
        self._refresh_recent()
        self.pages.setCurrentWidget(self.welcome)

    def show_convert(self) -> None:
        """Show the page that converts solver runs."""
        self.pages.setCurrentWidget(self.convert)
        self._status(
            "Add run folders or result files, choose the formats, "
            "then Convert"
        )

    @staticmethod
    def _local_files(event: Any) -> list[str]:
        data = event.mimeData()
        if not data.hasUrls():
            return []
        return [
            u.toLocalFile() for u in data.urls() if u.isLocalFile()
        ]

    def dragEnterEvent(self, event: Any) -> None:
        if self._local_files(event):
            event.acceptProposedAction()

    def dropEvent(self, event: Any) -> None:
        files = self._local_files(event)
        if not files:
            return
        event.acceptProposedAction()
        if self.pages.currentWidget() is self.convert:
            added = self.convert.add_sources(files)
            self._status(f"Added {added} source(s) to convert")
            return
        if self.open(files[0]) and len(files) > 1:
            self._status(
                f"Opened {Path(files[0]).name}, the first of "
                f"{len(files)} dropped items"
            )

    # ------------------------------------------------- export
    def _target(
        self, title: str, suffix: str, filt: str
    ) -> Path | None:
        loaded = self.view.loaded
        if loaded is None:
            return None
        stem = loaded.path.name.split(".")[0] or "model"
        start = Path(self._last_folder()) / f"{stem}{suffix}"
        path, _ = QFileDialog.getSaveFileName(
            self, title, str(start), filt
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
            self._run(lambda: self.view.save_figure(dst), dst)

    def _export_cells(self) -> None:
        dst = self._target("Export cells", "_cells.csv", "CSV (*.csv)")
        if dst is not None:
            self._run(
                lambda: summary.write_csv(
                    dst, *summary.cell_table(self.view.loaded.model)
                ),
                dst,
            )

    def _export_stations(self) -> None:
        dst = self._target(
            "Export stations", "_stations.csv", "CSV (*.csv)"
        )
        if dst is not None:
            self._run(
                lambda: summary.write_csv(
                    dst, *summary.station_rows(self.view.loaded.model)
                ),
                dst,
            )

    def _run(self, job: Any, dst: Path) -> bool:
        """Run a writing job; report its failure in a dialog."""
        error: Exception | None = None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            job()
        except Exception as exc:  # shown to the user, not hidden
            error = exc
        finally:
            QApplication.restoreOverrideCursor()
        if error is not None:
            self._fail("Cannot write", str(dst), error)
            return False
        self._status(f"Wrote {dst}")
        return True

    # --------------------------------------------------- help
    def _link(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def _shortcuts(self) -> None:
        rows = (
            ("Ctrl+O", "Open file"),
            ("Ctrl+Shift+O", "Open run folder"),
            ("Ctrl+Shift+C", "Convert solver runs"),
            ("F5", "Reload the model from disk"),
            ("Ctrl+Shift+S", "Save as"),
            ("Ctrl+E", "Export figure"),
            ("Ctrl+Home", "Start page"),
            ("Ctrl+1", "Show or hide the inspector"),
            ("Ctrl+2", "Collapse or expand the statistics"),
            ("Ctrl+T", "Switch light / dark theme"),
            ("F1", "This list"),
            ("Ctrl+Q", "Quit"),
        )
        body = "".join(
            f"<tr><td><b>{key}</b>&nbsp;&nbsp;&nbsp;</td>"
            f"<td>{what}</td></tr>"
            for key, what in rows
        )
        box = QMessageBox(self)
        box.setWindowTitle("Keyboard shortcuts")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(
            f"<table cellspacing='4'>{body}</table><br>"
            "Drop a file or a folder on the window to open it, or "
            "on the Convert page to add it to the list."
        )
        box.exec()

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

    def report_unexpected(
        self, kind: type, value: BaseException, tb: Any
    ) -> None:
        """Exception hook: show an unexpected error, keep running.

        Meant for ``sys.excepthook``, with its three arguments.
        ``KeyboardInterrupt`` goes to the default hook.
        """
        if issubclass(kind, KeyboardInterrupt):
            sys.__excepthook__(kind, value, tb)
            return
        self._fail(
            "Unexpected error",
            "PCSF Studio met an error it did not expect. You can "
            "keep working; please report it with the details below.",
            value.with_traceback(tb),
        )


def application() -> QApplication:
    """Return the running QApplication, creating one if needed.

    A new application uses the Fusion style, which follows the
    palette of the themes on every platform; an existing one is
    returned unchanged.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        app.setApplicationName("PCSF Studio")
        app.setOrganizationName("earthai-tech")
        app.setStyle("Fusion")
        app.setWindowIcon(logo_icon())
    return app
