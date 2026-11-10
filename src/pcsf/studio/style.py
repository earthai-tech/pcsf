"""Visual style of PCSF Studio: colours and the Qt style sheet.

One light theme, kept in one place so that the widgets carry only
object names (``setObjectName``) and properties, never colours.
"""

from __future__ import annotations

__all__ = ["ACCENT", "BAD", "GOOD", "STYLE_SHEET", "WARN"]

#: Accent colour (selection, primary buttons, histogram of the view).
ACCENT = "#2f5fd0"
#: Status colours of the header chips.
GOOD = "#1e8e5a"
WARN = "#b7791f"
BAD = "#c0392b"

_INK = "#1f2533"
_MUTED = "#6b7385"
_LINE = "#e2e6ee"
_PANEL = "#ffffff"
_BACK = "#f4f6fa"

STYLE_SHEET = f"""
QMainWindow, QWidget#Page {{ background: {_BACK}; }}
QWidget {{ color: {_INK}; font-size: 9.5pt; }}

QToolBar#MainBar {{
    background: {_PANEL}; border: none;
    border-bottom: 1px solid {_LINE}; padding: 4px 8px; spacing: 4px;
}}
QToolBar#MainBar QToolButton {{
    padding: 5px 10px; border-radius: 6px;
    border: 1px solid transparent;
}}
QToolBar#MainBar QToolButton:hover {{
    background: #eef2fb; border-color: #d5def3;
}}
QToolButton#HelpButton {{
    padding: 3px 8px; border-radius: 15px;
    border: 1px solid {_LINE}; background: {_BACK};
}}
QToolButton#HelpButton:hover {{ border-color: {ACCENT}; }}

QFrame#Card {{
    background: {_PANEL}; border: 1px solid {_LINE};
    border-radius: 10px;
}}
QLabel#Title {{ font-size: 14pt; font-weight: 600; }}
QLabel#Subtitle, QLabel#Muted {{ color: {_MUTED}; }}
QLabel#Section {{
    color: {_MUTED}; font-size: 8pt; font-weight: 600;
    letter-spacing: 1px;
}}
QLabel#Chip {{
    border-radius: 10px; padding: 2px 9px; font-size: 8.5pt;
    background: #eef1f7; color: {_INK};
}}
QLabel#Chip[status="good"] {{ background: #e3f4ec; color: {GOOD}; }}
QLabel#Chip[status="warn"] {{ background: #fbf1df; color: {WARN}; }}
QLabel#Chip[status="bad"] {{ background: #fbe5e2; color: {BAD}; }}

QFrame#Tile {{
    background: {_BACK}; border: 1px solid {_LINE}; border-radius: 8px;
}}
QLabel#TileLabel {{ color: {_MUTED}; font-size: 7.5pt; }}
QLabel#TileValue {{ font-size: 11pt; font-weight: 600; }}

QTabWidget::pane {{
    border: 1px solid {_LINE}; border-radius: 8px;
    background: {_PANEL};
    top: -1px;
}}
QTabBar::tab {{
    padding: 5px 10px; border: none; color: {_MUTED};
}}
QTabBar::tab:selected {{
    color: {ACCENT}; border-bottom: 2px solid {ACCENT};
}}
QTableWidget, QTreeWidget {{
    border: none; gridline-color: {_LINE};
    selection-background-color: #dfe7fa; selection-color: {_INK};
}}
QHeaderView::section {{
    background: {_BACK}; border: none;
    border-bottom: 1px solid {_LINE}; padding: 4px; color: {_MUTED};
}}

QPushButton {{
    padding: 6px 14px; border-radius: 6px;
    border: 1px solid {_LINE}; background: {_PANEL};
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton#Primary {{
    background: {ACCENT}; color: white; border-color: {ACCENT};
}}
QPushButton#Primary:hover {{ background: #2650b4; }}
QListWidget#Recent {{
    border: 1px solid {_LINE}; border-radius: 8px;
    background: {_PANEL};
}}

QComboBox, QDoubleSpinBox {{
    padding: 3px 6px; border: 1px solid {_LINE}; border-radius: 5px;
    background: {_PANEL};
}}
QSlider::groove:horizontal {{
    height: 4px; background: {_LINE}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px; margin: -6px 0; border-radius: 7px;
    background: {ACCENT};
}}
QStatusBar {{
    background: {_PANEL}; border-top: 1px solid {_LINE};
    color: {_MUTED};
}}
QSplitter::handle {{ background: transparent; width: 8px; }}
"""
