# -*- coding: utf-8 -*-
"""Word-style Ribbon for the PyQt6 PDFMind editor.

A ``QTabWidget`` whose tabs mirror Microsoft Word (File, Home, Insert, Design,
Layout, References, Mailings, Review, View, Help).  Each tab is a horizontal
strip of *groups*; a group shows its first command as a large icon-over-text
button and the rest as a small vertical stack, exactly like the Office ribbon.
Every button is wired to an existing command id handled by
:class:`win32.pyqt6_app.qat.QatRunner`, so there are no dead controls.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QTabWidget,
    QToolButton, QVBoxLayout, QWidget,
)

from win32.pyqt6_app.qat import FEATURES

_ICON_CACHE = {}


def make_emoji_icon(ch, size=32):
    """Render an emoji/unicode glyph to a QIcon (cached)."""
    key = (ch, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    font = QFont("Segoe UI Emoji")
    font.setPixelSize(int(size * 0.82))
    painter.setFont(font)
    painter.setPen(QColor("#1f1f1f"))
    painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, ch)
    painter.end()
    icon = QIcon(pm)
    _ICON_CACHE[key] = icon
    return icon


class RibbonButton(QToolButton):
    def __init__(self, fid, window, large=True):
        super().__init__()
        cmd = FEATURES[fid]
        self.fid = fid
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.setAutoRaise(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tip = cmd.label + (f"  ({cmd.accel})" if cmd.accel else "")
        self.setToolTip(tip)
        if cmd.accel:
            self.setShortcut(QKeySequence(cmd.accel))
        if large:
            self.setText(cmd.label)
            self.setIcon(make_emoji_icon(cmd.icon, 32))
            self.setIconSize(QSize(32, 32))
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            self.setStyleSheet(
                "QToolButton{padding:2px 6px;font-size:11px;}"
                "QToolButton:hover{background:#d5e3f0;border-radius:3px;}"
                "QToolButton:pressed{background:#bcd4ec;}")
        else:
            self.setText(cmd.label)
            self.setIcon(make_emoji_icon(cmd.icon, 18))
            self.setIconSize(QSize(18, 18))
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.setStyleSheet(
                "QToolButton{padding:1px 4px;font-size:11px;}"
                "QToolButton:hover{background:#d5e3f0;border-radius:3px;}"
                "QToolButton:pressed{background:#bcd4ec;}")
        self.clicked.connect(lambda _=False: window.qat.run(fid))


class RibbonGroup(QWidget):
    """A titled cluster of commands: first large, remainder small & stacked."""

    def __init__(self, title, fids, window):
        super().__init__()
        fids = [f for f in fids if f in FEATURES]
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 0)
        outer.setSpacing(2)

        row = QHBoxLayout()
        row.setSpacing(3)
        row.setAlignment(Qt.AlignmentFlag.AlignTop)
        if fids:
            row.addWidget(RibbonButton(fids[0], window, large=True))
            if len(fids) > 1:
                col = QVBoxLayout()
                col.setSpacing(1)
                col.setAlignment(Qt.AlignmentFlag.AlignTop)
                for fid in fids[1:]:
                    col.addWidget(RibbonButton(fid, window, large=False))
                col.addStretch(1)
                holder = QWidget()
                holder.setLayout(col)
                row.addWidget(holder)
        row.addStretch(1)
        outer.addLayout(row, 1)

        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color:#5a5a5a;font-size:10px;border:0px;")
        outer.addWidget(label)


class RibbonTab(QWidget):
    def __init__(self, groups, window):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        for i, (title, fids) in enumerate(groups):
            lay.addWidget(RibbonGroup(title, fids, window))
            if i < len(groups) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.VLine)
                sep.setFrameShadow(QFrame.Shadow.Plain)
                sep.setStyleSheet("color:#d9d9d9;")
                lay.addWidget(sep)
        lay.addStretch(1)


# Tab layout — every id resolves to a real QatRunner handler.
TABS = [
    ("File", [
        ("New / Open / Save", ["new", "open", "save", "save_as"]),
        ("Print", ["print", "print_all", "print_current"]),
        ("Export", ["export_images", "export_docx", "export_html", "export_svg"]),
    ]),
    ("Home", [
        ("Paste", ["paste", "paste_place", "cut", "copy"]),
        ("Edit", ["edit_element", "delete", "deselect", "clear_all"]),
        ("Font", ["font_color", "fill_color"]),
        ("AI", ["ai_extract", "ai_summarize"]),
        ("Editing", ["find_replace", "find_all"]),
    ]),
    ("Insert", [
        ("Pages", ["page_insert", "goto_page"]),
        ("Tables / Shapes", ["tool_rect", "tool_ellipse", "tool_triangle",
                             "tool_line", "tool_arrow"]),
        ("Illustrations", ["tool_image", "tool_text"]),
        ("Text", ["tool_note", "watermark", "header_footer", "tool_link",
                  "form_field"]),
    ]),
    ("Design", [
        ("Page Background", ["background", "watermark", "fill_color"]),
    ]),
    ("Layout", [
        ("Page Setup", ["rotate_cw", "rotate_ccw", "crop", "page_delete",
                        "page_duplicate"]),
        ("Arrange", ["measure_dist", "measure_area", "measure_perim"]),
    ]),
    ("References", [
        ("Bookmarks", ["bookmarks", "add_bookmark"]),
        ("Index", ["index", "find_all"]),
    ]),
    ("Mailings", [
        ("Batch", ["bates", "merge", "split"]),
    ]),
    ("Review", [
        ("Proofing", ["spellcheck", "a11y"]),
        ("Speech", ["read_aloud", "stop_reading"]),
        ("Annotations", ["tool_highlight", "tool_underline", "tool_strike",
                         "tool_note"]),
        ("Compare", ["compare"]),
        ("Protect", ["protect", "redact", "apply_redact"]),
    ]),
    ("View", [
        ("Zoom", ["zoom_in", "zoom_out", "zoom_fit", "zoom_width"]),
        ("Page", ["prev_page", "next_page"]),
        ("Tools", ["ocr_page", "compress", "pdfa", "opt_images"]),
    ]),
    ("Help", [
        ("Help", ["shortcuts", "about"]),
    ]),
]

RIBBON_STYLE = """
QTabWidget::pane {border:1px solid #c8c8c8; background:#f7f8fa; top:-1px;}
QTabBar::tab {background:#e8eaed; color:#262626; padding:6px 14px;
              margin-right:1px; border:1px solid #c8c8c8; border-bottom:none;
              font-size:12px;}
QTabBar::tab:selected {background:#f7f8fa; font-weight:bold; color:#1f3a5f;}
QTabBar::tab:hover:!selected {background:#dfe3e8;}
"""


class Ribbon(QTabWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.setStyleSheet(RIBBON_STYLE)
        self.setFixedHeight(120)
        self.tabbar = self.tabBar()
        for name, groups in TABS:
            self.addTab(RibbonTab(groups, window), name)
        # Give the File tab Word's roomier padding.
        self.tabBar().setTabText(0, "  File  ")

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(220)
        self.search.returnPressed.connect(self._run_search)
        corner = QWidget()
        cl = QHBoxLayout(corner)
        cl.setContentsMargins(0, 0, 8, 0)
        cl.addWidget(self.search)
        self.setCornerWidget(corner, Qt.Corner.TopRightCorner)

    def _run_search(self):
        text = self.search.text().strip()
        if text and hasattr(self.window, "search_from_box"):
            self.window.search_from_box(text)

    def refresh_enabled(self, has_document):
        # Buttons stay visible (Word shows them); handlers guard on their own.
        pass
