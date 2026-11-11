"""Visual style of PCSF Studio: themes and the Qt style sheet.

A :class:`Theme` is a named set of colours. The widgets carry only
object names (``setObjectName``) and properties, never colours, so
one call of :func:`style_sheet` restyles the whole application. Two
themes are defined, :data:`LIGHT` and :data:`DARK`; the name
``"system"`` follows the colour scheme of the desktop and is
resolved by the window (see
:meth:`pcsf.studio.window.StudioWindow.set_theme`).

This module needs no Qt.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ACCENT",
    "BAD",
    "DARK",
    "GOOD",
    "LIGHT",
    "STYLE_SHEET",
    "THEMES",
    "THEME_NAMES",
    "WARN",
    "Theme",
    "get_theme",
    "style_sheet",
]


@dataclass(frozen=True)
class Theme:
    """Colours of one theme, as ``#rrggbb`` strings.

    Parameters
    ----------
    name : str
        Identifier, ``"light"`` or ``"dark"``.
    dark : bool
        True when the background is darker than the text.
    back : str
        Window background, behind the cards.
    panel : str
        Background of cards, tables, inputs and the plot.
    raised : str
        Background of tiles and table headers.
    ink : str
        Text.
    muted : str
        Secondary text and axes lines.
    line : str
        Borders and grid lines.
    accent : str
        Selection, primary buttons, histogram of the view.
    accent_hover : str
        Primary button under the pointer.
    accent_soft : str
        Background of hovered toolbar buttons and menu items.
    accent_ink : str
        Text on *accent*.
    selection : str
        Background of selected table rows.
    chip : str
        Background of neutral header chips.
    good, warn, bad : str
        Status text colours of the header chips.
    good_back, warn_back, bad_back : str
        Their backgrounds.
    hist : str
        Histogram of the whole model.
    """

    name: str
    dark: bool
    back: str
    panel: str
    raised: str
    ink: str
    muted: str
    line: str
    accent: str
    accent_hover: str
    accent_soft: str
    accent_ink: str
    selection: str
    chip: str
    good: str
    warn: str
    bad: str
    good_back: str
    warn_back: str
    bad_back: str
    hist: str


#: Light theme (the default).
LIGHT = Theme(
    name="light",
    dark=False,
    back="#f4f6fa",
    panel="#ffffff",
    raised="#f4f6fa",
    ink="#1f2533",
    muted="#6b7385",
    line="#e2e6ee",
    accent="#2f5fd0",
    accent_hover="#2650b4",
    accent_soft="#eaf0fc",
    accent_ink="#ffffff",
    selection="#dfe7fa",
    chip="#eef1f7",
    good="#1e8e5a",
    warn="#b7791f",
    bad="#c0392b",
    good_back="#e3f4ec",
    warn_back="#fbf1df",
    bad_back="#fbe5e2",
    hist="#c9cfdb",
)

#: Dark theme.
DARK = Theme(
    name="dark",
    dark=True,
    back="#12151d",
    panel="#1b1f2b",
    raised="#232838",
    ink="#e6e9f2",
    muted="#99a2b8",
    line="#30364a",
    accent="#5b8af5",
    accent_hover="#779efa",
    accent_soft="#262f4a",
    accent_ink="#ffffff",
    selection="#2c3a63",
    chip="#2a3042",
    good="#4cc38a",
    warn="#e0a84a",
    bad="#f07a6c",
    good_back="#16332a",
    warn_back="#3a2e17",
    bad_back="#3f201d",
    hist="#465069",
)

#: Themes by name.
THEMES: dict[str, Theme] = {"light": LIGHT, "dark": DARK}
#: Names accepted by the window; ``"system"`` follows the desktop.
THEME_NAMES = ("system", "light", "dark")


def get_theme(name: str, system_dark: bool = False) -> Theme:
    """Return the theme of a name.

    Parameters
    ----------
    name : str
        One of :data:`THEME_NAMES`, in any case.
    system_dark : bool, default False
        Whether the desktop uses a dark colour scheme; only used
        for ``"system"``.

    Returns
    -------
    Theme
        :data:`LIGHT` or :data:`DARK`.

    Raises
    ------
    ValueError
        If *name* is not one of :data:`THEME_NAMES`.

    Examples
    --------
    >>> from pcsf.studio.style import get_theme
    >>> get_theme("dark").name
    'dark'
    >>> get_theme("system", system_dark=True).dark
    True
    """
    key = str(name).lower()
    if key == "system":
        return DARK if system_dark else LIGHT
    if key not in THEMES:
        raise ValueError(
            f"unknown theme {name!r}; use one of {THEME_NAMES}"
        )
    return THEMES[key]


def style_sheet(theme: Theme = LIGHT) -> str:
    """Qt style sheet of PCSF Studio for a theme.

    Parameters
    ----------
    theme : Theme, default LIGHT
        Colours to use.

    Returns
    -------
    str
        Style sheet for ``QWidget.setStyleSheet``. It styles by
        object name (``Card``, ``Chip``, ``Tile``, ``MainBar``...),
        so it can be set on a window or on an embedded
        :class:`~pcsf.studio.window.ModelView`.

    Examples
    --------
    >>> from pcsf.studio.style import DARK, style_sheet
    >>> DARK.panel in style_sheet(DARK)
    True
    """
    t = theme
    return f"""
QMainWindow, QDialog, QWidget#Page {{ background: {t.back}; }}
QWidget {{ color: {t.ink}; font-size: 9.5pt; }}
QWidget:disabled {{ color: {t.muted}; }}
QToolTip {{
    background: {t.raised}; color: {t.ink};
    border: 1px solid {t.line}; padding: 4px 6px;
}}

QMenuBar {{
    background: {t.panel}; border-bottom: 1px solid {t.line};
}}
QMenuBar::item {{
    padding: 4px 10px; background: transparent; border-radius: 5px;
}}
QMenuBar::item:selected {{ background: {t.accent_soft}; }}
QMenu {{
    background: {t.panel}; border: 1px solid {t.line};
    border-radius: 8px; padding: 5px;
}}
QMenu::item {{ padding: 5px 26px 5px 22px; border-radius: 5px; }}
QMenu::item:selected {{
    background: {t.accent_soft}; color: {t.ink};
}}
QMenu::item:disabled {{ color: {t.muted}; }}
QMenu::separator {{
    height: 1px; background: {t.line}; margin: 5px 8px;
}}

QToolBar#MainBar {{
    background: {t.panel}; border: none;
    border-bottom: 1px solid {t.line}; padding: 5px 10px;
    spacing: 4px;
}}
QToolBar#MainBar::separator {{
    width: 1px; background: {t.line}; margin: 6px 6px;
}}
QToolBar#MainBar QToolButton {{
    padding: 5px 10px; border-radius: 6px;
    border: 1px solid transparent;
}}
QToolBar#MainBar QToolButton:hover {{
    background: {t.accent_soft};
}}
QToolBar#MainBar QToolButton:pressed {{
    background: {t.selection};
}}
QToolButton#Brand {{ font-size: 10.5pt; font-weight: 600; }}
QToolBar#MainBar QToolButton#Round {{
    min-width: 28px; max-width: 28px;
    min-height: 28px; max-height: 28px; padding: 0;
    border-radius: 14px; border: 1px solid {t.line};
    background: {t.raised}; font-weight: 700;
}}
QToolBar#MainBar QToolButton#Round:hover {{
    border-color: {t.accent}; color: {t.accent};
}}
QToolButton#Brand::menu-indicator,
QToolButton#Round::menu-indicator {{ image: none; }}
/* A real colour, not transparent: matplotlib picks its light or
   dark toolbar icons from the background of the toolbar. */
QToolBar#PlotBar {{
    background: {t.panel}; border: none; spacing: 2px;
}}
QToolBar#PlotBar QToolButton {{
    padding: 3px; border-radius: 5px;
    border: 1px solid transparent;
}}
QToolBar#PlotBar QToolButton:hover {{
    background: {t.accent_soft};
}}
QToolBar#PlotBar QToolButton:checked {{
    background: {t.selection}; border-color: {t.accent};
}}

QScrollArea#Scroll, QScrollArea#Scroll > QWidget,
QWidget#ScrollBody {{
    background: transparent; border: none;
}}

QFrame#Card {{
    background: {t.panel}; border: 1px solid {t.line};
    border-radius: 10px;
}}
QFrame#Rule {{
    background: {t.line}; border: none;
    min-height: 1px; max-height: 1px;
}}
QLabel#Title {{ font-size: 14pt; font-weight: 600; }}
QLabel#Hero {{ font-size: 19pt; font-weight: 600; }}
QLabel#Subtitle, QLabel#Muted {{ color: {t.muted}; }}
QLabel#Section {{
    color: {t.muted}; font-size: 8pt; font-weight: 600;
    letter-spacing: 1px;
}}
QLabel#Chip {{
    border-radius: 10px; padding: 2px 9px; font-size: 8.5pt;
    background: {t.chip}; color: {t.ink};
}}
QLabel#Chip[status="good"] {{
    background: {t.good_back}; color: {t.good};
}}
QLabel#Chip[status="warn"] {{
    background: {t.warn_back}; color: {t.warn};
}}
QLabel#Chip[status="bad"] {{
    background: {t.bad_back}; color: {t.bad};
}}

QFrame#Tile {{
    background: {t.raised}; border: 1px solid {t.line};
    border-radius: 8px;
}}
QLabel#TileLabel {{ color: {t.muted}; font-size: 7.5pt; }}
QLabel#TileValue {{ font-size: 11pt; font-weight: 600; }}

QTabWidget::pane {{
    border: 1px solid {t.line}; border-radius: 8px;
    background: {t.panel};
    top: -1px;
}}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    padding: 6px 11px; border: none; color: {t.muted};
    background: transparent;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{ color: {t.ink}; }}
QTabBar::tab:selected {{
    color: {t.accent}; border-bottom: 2px solid {t.accent};
}}
QTabBar QToolButton {{
    background: {t.panel}; border: 1px solid {t.line};
    border-radius: 4px;
}}
QTableWidget, QTreeWidget {{
    border: none; gridline-color: {t.line};
    background: {t.panel}; alternate-background-color: {t.raised};
    selection-background-color: {t.selection};
    selection-color: {t.ink};
}}
QHeaderView {{ background: {t.raised}; }}
QHeaderView::section {{
    background: {t.raised}; border: none;
    border-bottom: 1px solid {t.line}; padding: 5px 6px;
    color: {t.muted};
}}
QTableCornerButton::section {{
    background: {t.raised}; border: none;
}}

QPushButton {{
    padding: 6px 14px; border-radius: 6px;
    border: 1px solid {t.line}; background: {t.panel};
}}
QPushButton:hover {{ border-color: {t.accent}; }}
QPushButton:pressed {{ background: {t.accent_soft}; }}
QPushButton#Primary {{
    background: {t.accent}; color: {t.accent_ink};
    border-color: {t.accent}; font-weight: 600;
}}
QPushButton#Primary:hover {{ background: {t.accent_hover}; }}
QListWidget#Recent {{
    border: 1px solid {t.line}; border-radius: 8px;
    background: {t.panel}; padding: 4px; outline: none;
    activate-on-singleclick: 1;
}}
QListWidget#Recent::item {{
    padding: 5px 8px; border-radius: 6px;
}}
QListWidget#Recent::item:hover {{ background: {t.accent_soft}; }}
QListWidget#Recent::item:selected {{
    background: {t.selection}; color: {t.ink};
}}

QLineEdit, QPlainTextEdit#Log {{
    padding: 4px 6px; border: 1px solid {t.line};
    border-radius: 5px; background: {t.panel};
    selection-background-color: {t.selection};
    selection-color: {t.ink};
}}
QLineEdit:focus {{ border-color: {t.accent}; }}
QPlainTextEdit#Log {{ background: {t.raised}; }}
QProgressBar {{
    border: 1px solid {t.line}; border-radius: 5px;
    background: {t.raised}; text-align: center; min-height: 18px;
    color: {t.ink};
}}
QProgressBar::chunk {{
    background: {t.accent}; border-radius: 4px;
}}

QComboBox, QDoubleSpinBox {{
    padding: 3px 6px; border: 1px solid {t.line};
    border-radius: 5px; background: {t.panel};
    selection-background-color: {t.selection};
    selection-color: {t.ink};
}}
QComboBox:hover, QDoubleSpinBox:hover,
QComboBox:focus, QDoubleSpinBox:focus {{
    border-color: {t.accent};
}}
QComboBox QAbstractItemView {{
    background: {t.panel}; border: 1px solid {t.line};
    selection-background-color: {t.selection};
    selection-color: {t.ink}; outline: none;
}}
QSlider::groove:horizontal {{
    height: 4px; background: {t.line}; border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {t.accent}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px; margin: -6px 0; border-radius: 7px;
    background: {t.accent}; border: 2px solid {t.panel};
}}
QSlider::handle:horizontal:disabled {{ background: {t.muted}; }}
QSlider::sub-page:horizontal:disabled {{ background: {t.line}; }}

QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px;
}}
QScrollBar:horizontal {{
    background: transparent; height: 10px; margin: 2px;
}}
QScrollBar::handle {{
    background: {t.line}; border-radius: 3px;
    min-width: 24px; min-height: 24px;
}}
QScrollBar::handle:hover {{ background: {t.muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0; height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

QStatusBar {{
    background: {t.panel}; border-top: 1px solid {t.line};
    color: {t.muted};
}}
QStatusBar::item {{ border: none; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 8px; }}
QSplitter::handle:hover {{ background: {t.accent_soft}; }}
"""


#: Accent colour of the light theme; kept for code written against
#: the first version, like the four names below.
ACCENT = LIGHT.accent
GOOD = LIGHT.good
WARN = LIGHT.warn
BAD = LIGHT.bad
#: Style sheet of the light theme, ``style_sheet(LIGHT)``.
STYLE_SHEET = style_sheet(LIGHT)
