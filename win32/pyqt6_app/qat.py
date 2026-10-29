# -*- coding: utf-8 -*-
"""PyQt6 Quick-Access Toolbar (QAT).

A customizable command strip with the same command ids as the legacy tkinter
QAT, so an existing ``~/.pdf_editor_qat.json`` layout carries over unchanged.
Every command resolves to a real handler on the PyQt6 window (controller /
canvas / FeatureActions) where a backend exists; commands whose subsystem is
not part of this build respond with an informative dialog instead of doing
nothing.
"""
from __future__ import annotations

import copy
import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QKeySequence, QAction
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog,
    QGroupBox, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QPushButton, QScrollArea, QToolBar, QToolButton,
    QVBoxLayout, QWidget,
)

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".pdf_editor_qat.json")
DEFAULT_ITEMS = ["save", "undo", "redo", "print"]
CATEGORIES = ["File", "Edit", "Insert", "Annotate", "Page", "Tools", "View", "Help"]
POPULAR = ["new", "open", "save", "print", "undo", "redo", "cut", "copy",
           "paste", "find_all", "zoom_in", "zoom_out", "export_images"]


class Command:
    __slots__ = ("fid", "category", "label", "icon", "accel")

    def __init__(self, fid, category, label, icon, accel=""):
        self.fid, self.category, self.label, self.icon, self.accel = (
            fid, category, label, icon, accel)


# Command catalog — ids match the legacy tkinter QAT.
_CATALOG = [
    Command("new", "File", "New Document", "\U0001f4c4", "Ctrl+N"),
    Command("open", "File", "Open PDF", "\U0001f4c2", "Ctrl+O"),
    Command("save", "File", "Save", "\U0001f4be", "Ctrl+S"),
    Command("save_as", "File", "Save As", "\U0001f4ab", "Ctrl+Shift+S"),
    Command("print", "File", "Print", "\U0001f5a8", "Ctrl+P"),
    Command("print_all", "File", "Print All Pages", "\U0001f5a7"),
    Command("print_current", "File", "Print Current Page", "\U0001f5a6"),
    Command("export_images", "File", "Export to Images", "\U0001f5bc"),
    Command("export_docx", "File", "Export to DOCX", "\U0001f4c5"),
    Command("export_html", "File", "Export to HTML", "\U0001f310"),
    Command("export_svg", "File", "Export to SVG", "\U0001f58c"),

    Command("undo", "Edit", "Undo", "\u21b6", "Ctrl+Z"),
    Command("redo", "Edit", "Redo", "\u21b7", "Ctrl+Y"),
    Command("cut", "Edit", "Cut", "\u2702", "Ctrl+X"),
    Command("copy", "Edit", "Copy", "\U0001f4cb", "Ctrl+C"),
    Command("paste", "Edit", "Paste", "\U0001f4ea", "Ctrl+V"),
    Command("paste_place", "Edit", "Paste in Place", "\U0001f4cc"),
    Command("delete", "Edit", "Delete Selected", "\U0001f5d1", "Del"),
    Command("deselect", "Edit", "Deselect", "\u274c", "Esc"),
    Command("edit_element", "Edit", "Edit Selected", "\u270e"),
    Command("find_replace", "Edit", "Find & Replace", "\U0001f50d", "Ctrl+H"),
    Command("clear_all", "Edit", "Clear All Elements", "\U0001f9f9"),

    Command("tool_text", "Insert", "Add Text", "\U0001f520"),
    Command("tool_image", "Insert", "Add Image", "\U0001f5bc"),
    Command("tool_rect", "Insert", "Rectangle", "\u25a1"),
    Command("tool_ellipse", "Insert", "Ellipse", "\u25cb"),
    Command("tool_triangle", "Insert", "Triangle", "\u25b3"),
    Command("tool_line", "Insert", "Line", "\u2571"),
    Command("tool_arrow", "Insert", "Arrow", "\u27a4"),
    Command("watermark", "Insert", "Watermark", "\U0001f4a7"),
    Command("header_footer", "Insert", "Page Numbers", "\U0001f4c4"),
    Command("form_field", "Insert", "Detect Form Fields", "\U0001f9fe"),
    Command("tool_link", "Insert", "Hyperlink", "\U0001f517"),

    Command("tool_highlight", "Annotate", "Highlight", "\U0001f58e"),
    Command("tool_underline", "Annotate", "Underline", "\u0336"),
    Command("tool_strike", "Annotate", "Strikethrough", "\u0335"),
    Command("tool_note", "Annotate", "Sticky Note", "\U0001f4dd"),
    Command("redact", "Annotate", "Mark Redaction", "\u2593"),
    Command("apply_redact", "Annotate", "Apply Redactions", "\u26a0"),
    Command("measure_dist", "Annotate", "Measure Distance", "\U0001f4cf"),
    Command("measure_area", "Annotate", "Measure Area", "\u259d"),
    Command("measure_perim", "Annotate", "Measure Perimeter", "\u2599"),

    Command("page_insert", "Page", "Insert Page", "\U0001f4be"),
    Command("page_delete", "Page", "Delete Page", "\U0001f5d1"),
    Command("page_duplicate", "Page", "Duplicate Page", "\U0001f4d8"),
    Command("rotate_cw", "Page", "Rotate Clockwise", "\u21bb"),
    Command("rotate_ccw", "Page", "Rotate Counter-CW", "\u21ba"),
    Command("crop", "Page", "Crop Page", "\u2702"),
    Command("merge", "Page", "Merge PDFs", "\U0001f4d6"),
    Command("split", "Page", "Split PDF", "\U0001f4d4"),
    Command("bates", "Page", "Bates Numbering", "\U0001f522"),
    Command("background", "Page", "Set Background", "\U0001f3a8"),

    Command("bookmarks", "Tools", "Bookmarks", "\U0001f516"),
    Command("add_bookmark", "Tools", "Add Bookmark", "\U0001f516"),
    Command("ocr_page", "Tools", "OCR", "\U0001f9dd"),
    Command("protect", "Tools", "Password Protect", "\U0001f512"),
    Command("ai_extract", "Tools", "AI: Extract Text", "\u2728"),
    Command("ai_summarize", "Tools", "AI: Summarize", "\U0001f9e0"),
    Command("compare", "Tools", "Compare Documents", "\U0001f500", "Ctrl+Shift+C"),
    Command("compress", "Tools", "Compress PDF", "\U0001f4e6"),
    Command("opt_images", "Tools", "Optimize Images", "\U0001f387"),
    Command("pdfa", "Tools", "PDF/A Compliance", "\U0001f3c5"),
    Command("spellcheck", "Tools", "Spell Check", "\u2714", "F7"),
    Command("read_aloud", "Tools", "Read Aloud", "\U0001f50a", "F5"),
    Command("stop_reading", "Tools", "Stop Reading", "\U0001f4a4"),
    Command("a11y", "Tools", "Accessibility Check", "\u267f"),
    Command("index", "Tools", "Full-Text Index", "\U0001f4cf"),
    Command("find_all", "Tools", "Find in All Pages", "\U0001f50e", "Ctrl+Shift+F"),

    Command("prev_page", "View", "Previous Page", "\u23ee"),
    Command("next_page", "View", "Next Page", "\u23ed"),
    Command("goto_page", "View", "Go to Page", "\U0001f170"),
    Command("zoom_in", "View", "Zoom In", "\U0001f536", "Ctrl++"),
    Command("zoom_out", "View", "Zoom Out", "\U0001f53a", "Ctrl+-"),
    Command("zoom_fit", "View", "Fit Page", "\u26f5"),
    Command("zoom_width", "View", "Fit Width", "\u2194"),
    Command("font_color", "View", "Font Color", "\U0001f534"),
    Command("fill_color", "View", "Fill Color", "\U0001f7e1"),

    Command("shortcuts", "Help", "Keyboard Shortcuts", "\u2328", "F1"),
    Command("about", "Help", "About", "\u2139"),
]

FEATURES = {c.fid: c for c in _CATALOG}


def load_config():
    """Return {items, labels, position}; backward-compatible with old files."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        data = {}
    items = [fid for fid in data.get("items", []) if fid in FEATURES] or list(DEFAULT_ITEMS)
    return {
        "items": items,
        "labels": bool(data.get("labels", False)),
        "position": data.get("position", "above"),  # "above" | "below"
    }


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump({
                "items": [f for f in cfg.get("items", []) if f in FEATURES],
                "labels": bool(cfg.get("labels", False)),
                "position": cfg.get("position", "above"),
            }, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


# Legacy helpers kept for compatibility.
def load_items():
    return load_config()["items"]


def save_items(items):
    cfg = load_config()
    cfg["items"] = items
    save_config(cfg)


class QatRunner:
    """Resolves QAT command ids to live callables on the window."""

    def __init__(self, window):
        self.win = window
        self.controller = window.controller
        self.clipboard_element = None
        self.map = {}
        self._build()

    # -- helpers -----------------------------------------------------
    def _reg(self, *fids):
        def deco(fn):
            for f in fids:
                self.map[f] = fn
            return fn
        return deco

    def _feature(self, name):
        feat = getattr(self.win, "features", None)
        return getattr(feat, name, None) if feat else None

    def _require_doc(self):
        if not self.controller.has_document:
            QMessageBox.information(self.win, "No document", "Open a PDF first.")
            return False
        return True

    def _not_available(self, label):
        QMessageBox.information(
            self.win, label,
            f"{label} needs a subsystem that is not part of the current "
            "PyQt6 build yet.")

    def run(self, fid):
        fn = self.map.get(fid)
        if fn is None:
            c = FEATURES.get(fid)
            self._not_available(c.label if c else fid)
            return
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self.win, FEATURES.get(fid).label, str(e))

    # -- build the dispatch table ------------------------------------
    def _build(self):
        c = self.controller
        w = self.win

        # File
        self.map["new"] = w.new_document
        self.map["open"] = w.on_open
        self.map["save"] = w.on_save
        self.map["save_as"] = w.on_save_as
        self.map["print"] = lambda: self.print_pdf("all")
        self.map["print_all"] = lambda: self.print_pdf("all")
        self.map["print_current"] = lambda: self.print_pdf("current")
        for fid, meth in (("export_images", "export_images"),
                          ("export_docx", "export_docx"),
                          ("export_html", "export_html")):
            fn = self._feature(meth)
            self.map[fid] = fn if fn else (lambda m=meth: self._not_available(m))
        self.map["export_svg"] = self.export_svg

        # Edit
        self.map["undo"] = c.undo
        self.map["redo"] = c.redo
        self.map["cut"] = self.cut
        self.map["copy"] = self.copy
        self.map["paste"] = lambda: self.paste(offset=True)
        self.map["paste_place"] = lambda: self.paste(offset=False)
        self.map["delete"] = c.remove_selected
        self.map["deselect"] = lambda: c.select(None)
        self.map["edit_element"] = self.edit_element
        self.map["find_replace"] = lambda: (self._feature("find_text") or
                                            (lambda: self._not_available("Find")))()
        self.map["clear_all"] = self.clear_all

        # Insert
        self.map["tool_text"] = w.on_add_text
        self.map["tool_image"] = w.on_add_image
        self.map["tool_rect"] = lambda: self.insert_shape("rect")
        self.map["tool_ellipse"] = lambda: self.insert_shape("ellipse")
        self.map["tool_triangle"] = lambda: self.insert_shape("triangle")
        self.map["tool_line"] = lambda: self.insert_line(arrow=False)
        self.map["tool_arrow"] = lambda: self.insert_line(arrow=True)
        for fid, meth in (("watermark", "add_text_watermark"),
                          ("header_footer", "add_page_numbers"),
                          ("form_field", "detect_form_fields"),
                          ("tool_link", "add_link")):
            fn = self._feature(meth)
            self.map[fid] = fn if fn else (lambda m=meth: self._not_available(m))

        # Annotate
        self.map["tool_highlight"] = self.insert_highlight
        self.map["tool_underline"] = lambda: self.insert_annotation("underline")
        self.map["tool_strike"] = lambda: self.insert_annotation("strikethrough")
        self.map["tool_note"] = self.insert_note
        for fid, meth in (("redact", "mark_redaction"),
                          ("apply_redact", "apply_redactions"),
                          ("measure_dist", "measure_distance")):
            fn = self._feature(meth)
            self.map[fid] = fn if fn else (lambda m=meth: self._not_available(m))
        self.map["measure_area"] = lambda: self._measure("area")
        self.map["measure_perim"] = lambda: self._measure("perimeter")

        # Page (all delegate to FeatureActions)
        page_map = {
            "page_insert": "add_page", "page_delete": "delete_page",
            "page_duplicate": "duplicate_page", "crop": "crop_page",
            "merge": "merge_pdfs", "split": "split_pdf",
            "bates": "bates_all_pages", "background": "set_background",
        }
        for fid, meth in page_map.items():
            fn = self._feature(meth)
            self.map[fid] = fn if fn else (lambda m=meth: self._not_available(m))
        self.map["rotate_cw"] = lambda: c.rotate_current(90)
        self.map["rotate_ccw"] = lambda: c.rotate_current(-90)

        # Tools
        for fid, meth in (("bookmarks", "list_bookmarks"),
                          ("add_bookmark", "add_bookmark"),
                          ("ocr_page", "run_ocr"),
                          ("protect", "set_password"),
                          ("ai_extract", "ai_extract"),
                          ("ai_summarize", "ai_summarize"),
                          ("compare", "compare"),
                          ("compress", "compress"),
                          ("pdfa", "validate_pdfa"),
                          ("spellcheck", "spellcheck_page"),
                          ("read_aloud", "tts_page"),
                          ("stop_reading", "tts_stop"),
                          ("a11y", "check_accessibility"),
                          ("find_all", "find_text")):
            fn = self._feature(meth)
            self.map[fid] = fn if fn else (lambda m=meth: self._not_available(m))
        self.map["opt_images"] = self.optimize_images
        self.map["index"] = self.build_index

        # View
        self.map["prev_page"] = c.prev_page
        self.map["next_page"] = c.next_page
        self.map["goto_page"] = self.goto_page
        self.map["zoom_in"] = c.zoom_in
        self.map["zoom_out"] = c.zoom_out
        self.map["zoom_fit"] = w.canvas.fit_to_view
        self.map["zoom_width"] = self.fit_width
        self.map["font_color"] = self.pick_font_color
        self.map["fill_color"] = self.pick_fill_color

        # Help
        self.map["shortcuts"] = self.show_shortcuts
        self.map["about"] = w.on_about

    # ==================================================================
    # Newly implemented commands
    # ==================================================================
    def print_pdf(self, scope):
        if not self._require_doc():
            return
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        from PyQt6.QtGui import QImage
        import pymupdf
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(printer, self.win)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        doc = self.controller.doc
        pages = ([self.controller.current_page] if scope == "current"
                 else list(range(len(doc))))
        painter = QPainter(printer)
        rect = printer.pageRect(QPrinter.Unit.DevicePixel)
        for n, p in enumerate(pages):
            pix = doc[p].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.bytesPerLine,
                         QImage.Format.Format_RGB888).copy()
            # scale image to fit the printable page rect, preserving aspect
            target = rect.size()
            scaled = img.scaled(target.width(), target.height(),
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
            x = rect.x() + (target.width() - scaled.width()) / 2
            y = rect.y() + (target.height() - scaled.height()) / 2
            painter.drawImage(int(x), int(y), scaled)
            if n < len(pages) - 1:
                printer.newPage()
        painter.end()
        self.win._set_status(f"Printed {len(pages)} page(s)")

    def export_svg(self):
        if not self._require_doc():
            return
        out, _ = QFileDialog.getSaveFileName(self.win, "Export SVG", "page.svg",
                                             "SVG Image (*.svg)")
        if not out:
            return
        page = self.controller.page()
        svg = page.get_svg_image()
        with open(out, "w", encoding="utf-8") as f:
            f.write(svg)
        self.win._set_status(f"Exported {os.path.basename(out)}")

    def cut(self):
        self.copy()
        if self.controller.selected_index is not None:
            self.controller.remove_selected()

    def copy(self):
        if not self._require_doc():
            return
        elem = self.controller.selected_element()
        if elem is None:
            self.win._set_status("Nothing selected to copy")
            return
        self.clipboard_element = copy.deepcopy(elem)
        self.win._set_status("Copied element")

    def paste(self, offset=True):
        if not self._require_doc():
            return
        if self.clipboard_element is None:
            self.win._set_status("Clipboard empty")
            return
        elem = copy.deepcopy(self.clipboard_element)
        elem.page = self.controller.current_page
        if offset:
            self.controller._apply_delta(elem, 10, -10)
        self.controller.add_element(elem)

    def edit_element(self):
        if not self._require_doc():
            return
        elem = self.controller.selected_element()
        if elem is None:
            self.win._set_status("Select an element to edit")
            return
        if hasattr(elem, "text"):
            new, ok = QInputDialog.getText(self.win, "Edit text", "Text:",
                                           text=getattr(elem, "text", ""))
            if ok:
                elem.text = new
                self.controller.set_modified(True)
                self.controller.elements_changed.emit()

    def clear_all(self):
        if not self._require_doc():
            return
        if QMessageBox.question(self.win, "Clear all",
                                "Remove all editable elements on this document?") \
                != QMessageBox.StandardButton.Yes:
            return
        self.controller._push_undo()
        self.controller.elements = []
        self.controller.set_modified(True)
        self.controller.elements_changed.emit()
        self.win._set_status("Cleared all elements")

    def insert_shape(self, kind):
        if not self._require_doc():
            return
        from win32.models.elements import ShapeElement
        color = self._pick_color("#ff0000") or "#ff0000"
        w = QInputDialog.getDouble(self.win, "Width", "Width (pt):", 150, 5, 3000, 1)
        h = QInputDialog.getDouble(self.win, "Height", "Height (pt):", 100, 5, 3000, 1)
        if w[1] and h[1]:
            self.controller.add_element(ShapeElement(
                shape_type=kind, x=72, y=72, w=w[0], h=h[0], color=color,
                page=self.controller.current_page))

    def insert_line(self, arrow=False):
        if not self._require_doc():
            return
        from win32.models.elements import LineElement
        color = self._pick_color("#ff0000") or "#ff0000"
        self.controller.add_element(LineElement(
            x1=72, y1=72, x2=220, y2=160, color=color,
            page=self.controller.current_page))
        if arrow:
            self.win._set_status("Arrow added as a line (heads not rendered yet)")

    def insert_highlight(self):
        if not self._require_doc():
            return
        from win32.models.elements import HighlightElement
        color = self._pick_color("#FFFF00") or "#FFFF00"
        self.controller.add_element(HighlightElement(
            x=72, y=100, w=200, h=20, color=color,
            page=self.controller.current_page))

    def insert_annotation(self, style):
        if not self._require_doc():
            return
        from win32.models.elements import AnnotationElement
        self.controller.add_element(AnnotationElement(
            x=72, y=100, w=200, h=16, style=style,
            page=self.controller.current_page))

    def insert_note(self):
        if not self._require_doc():
            return
        from win32.models.elements import NoteElement
        text, ok = QInputDialog.getText(self.win, "Sticky note", "Note text:")
        if ok:
            self.controller.add_element(NoteElement(
                x=72, y=72, text=text, page=self.controller.current_page))

    def _measure(self, kind):
        if not self._require_doc():
            return
        raw, ok = QInputDialog.getText(self.win, "Measure",
                                       "Points as x,y pairs (e.g. 0,0 100,0 100,50):")
        if not ok or not raw.strip():
            return
        points = []
        for chunk in raw.replace(";", " ").split():
            if "," in chunk:
                a, b = chunk.split(",", 1)
                points.append((float(a), float(b)))
        svc = self.win.facade.measurement_service
        result = svc.measure_area(points) if kind == "area" else svc.measure_perimeter(points)
        QMessageBox.information(self.win, "Measurement", str(result))

    def optimize_images(self):
        if not self._require_doc() or not self.controller.path:
            return
        q = QInputDialog.getInt(self.win, "Optimize images", "JPEG quality:", 70, 1, 100)
        if q[1]:
            self.win.facade.compress_service.optimize_images(self.controller.path, q[0])
            self.win._set_status("Images optimized")

    def build_index(self):
        if not self._require_doc() or not self.controller.path:
            return
        self.win.facade.index_service.build_index(self.controller.path)
        self.win._set_status("Full-text index rebuilt")

    def goto_page(self):
        if not self._require_doc():
            return
        n, ok = QInputDialog.getInt(self.win, "Go to page", "Page (1-based):",
                                    self.controller.current_page + 1, 1,
                                    max(1, self.controller.total_pages))
        if ok:
            self.controller.set_current_page(n - 1)

    def fit_width(self):
        page = self.controller.page()
        if page is None:
            return
        vp = self.win.canvas.viewport().width()
        self.controller.set_zoom(vp / page.rect.width * 100)

    def pick_font_color(self):
        elem = self.controller.selected_element()
        if elem is None or not hasattr(elem, "color"):
            self.win._set_status("Select a text element first")
            return
        color = self._pick_color(getattr(elem, "color", "#000000"))
        if color:
            elem.color = color
            self.controller.set_modified(True)
            self.controller.elements_changed.emit()

    def pick_fill_color(self):
        elem = self.controller.selected_element()
        if elem is None:
            self.win._set_status("Select a shape first")
            return
        color = self._pick_color(getattr(elem, "color", "#ff0000"))
        if color:
            if hasattr(elem, "fill_color"):
                elem.fill_color = color
            if hasattr(elem, "color"):
                elem.color = color
            self.controller.set_modified(True)
            self.controller.elements_changed.emit()

    def show_shortcuts(self):
        lines = [f"{c.accel:16}  {c.label}" for c in _CATALOG if c.accel]
        QMessageBox.information(self.win, "Keyboard Shortcuts", "\n".join(lines))

    def _pick_color(self, default="#000000"):
        chosen = QColorDialog.getColor(QColor(default), self.win, "Choose color")
        return chosen.name() if chosen.isValid() else None


class QuickAccessToolbar(QToolBar):
    """Word-style Quick Access Toolbar: command strip + a ▼ dropdown that
    toggles commands, opens the More-Commands dialog, switches position and
    hides itself."""

    def __init__(self, window):
        super().__init__("Quick Access", window)
        self.window = window
        self.setObjectName("QAT")
        self.setMovable(False)
        cfg = load_config()
        self.items = cfg["items"]
        self._labels = cfg["labels"]
        self._position = cfg["position"]
        self.setContentsMargins(4, 2, 4, 2)
        self.rebuild()

    # -- rendering ----------------------------------------------------
    def _text_for(self, cmd):
        return f"{cmd.icon} {cmd.label}" if self._labels else cmd.icon

    def rebuild(self):
        self.clear()
        for fid in self.items:
            cmd = FEATURES.get(fid)
            if cmd is None:
                continue
            act = QAction(self._text_for(cmd), self)
            act.setToolTip(f"{cmd.label}" + (f"  ({cmd.accel})" if cmd.accel else ""))
            if cmd.accel:
                act.setShortcut(QKeySequence(cmd.accel))
            act.triggered.connect(lambda _=False, f=fid: self.window.qat.run(f))
            self.addAction(act)
        self._add_dropdown()

    def _add_dropdown(self):
        btn = QToolButton()
        btn.setText("\u25bc")  # ▼
        btn.setToolTip("Customize Quick Access Toolbar")
        btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        btn.setMenu(self._build_menu())
        self.addWidget(btn)

    def _build_menu(self):
        menu = QMenu(self)
        for category in CATEGORIES:
            menu.addSection(category)
            for cmd in _CATALOG:
                if cmd.category != category:
                    continue
                act = QAction(cmd.label, menu)
                act.setCheckable(True)
                act.setChecked(cmd.fid in self.items)
                act.toggled.connect(lambda on, f=cmd.fid: self._toggle_item(f, on))
                menu.addAction(act)
        menu.addSeparator()
        menu.addAction("More Commands\u2026", self.open_customize)
        pos_label = ("Show Below the Ribbon" if self._position == "above"
                     else "Show Above the Ribbon")
        menu.addAction(pos_label, self.toggle_position)
        menu.addAction("Hide Quick Access Toolbar", self.hide)
        return menu

    # -- mutation -----------------------------------------------------
    def _toggle_item(self, fid, on):
        if on and fid not in self.items:
            self.items.append(fid)
        elif not on and fid in self.items:
            self.items.remove(fid)
        if not self.items:
            self.items = [fid]
        self._persist()
        self.rebuild()

    def set_items(self, fids, labels=None, position=None):
        self.items = [f for f in fids if f in FEATURES] or list(DEFAULT_ITEMS)
        if labels is not None:
            self._labels = bool(labels)
        if position is not None:
            self._position = position
        self._persist()
        self.rebuild()
        self.window.apply_qat_position(self._position)

    def reset_defaults(self):
        self.set_items(list(DEFAULT_ITEMS), labels=False, position="above")

    def toggle_position(self):
        self._position = "below" if self._position == "above" else "above"
        self._persist()
        self.window.apply_qat_position(self._position)

    def _persist(self):
        save_config({"items": self.items, "labels": self._labels,
                     "position": self._position})

    def open_customize(self):
        CustomizeDialog(self).exec()

    @property
    def show_labels(self):
        return self._labels

    @property
    def position(self):
        return self._position


class CustomizeDialog(QDialog):
    """Word-style 'Customize the Quick Access Toolbar' dialog: choose-commands-
    from filter, Add/Remove between two lists, reorder arrows, position/labels
    options, Reset and Import/Export."""

    def __init__(self, qat):
        super().__init__(qat.window)
        self.qat = qat
        self._ordered = list(qat.items)
        self.setWindowTitle("Customize the Quick Access Toolbar")
        self.resize(760, 520)

        root = QVBoxLayout(self)
        panes = QHBoxLayout()

        # Left: choose-from + available list
        left = QVBoxLayout()
        left.addWidget(QLabel("Choose commands from:"))
        self.choose_combo = QComboBox()
        self.choose_combo.addItems(["Popular Commands", "All Commands"] + CATEGORIES)
        self.choose_combo.currentIndexChanged.connect(self._populate_available)
        left.addWidget(self.choose_combo)
        self.available = QListWidget()
        self.available.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        left.addWidget(self.available, 1)
        panes.addLayout(left, 1)

        # Middle: Add / Remove
        mid = QVBoxLayout()
        mid.addStretch(1)
        mid.addWidget(QPushButton("Add >>", clicked=self._add))
        mid.addWidget(QPushButton("<< Remove", clicked=self._remove))
        mid.addStretch(1)
        panes.addLayout(mid, 0)

        # Right: scope + current order + reorder arrows
        rightcol = QVBoxLayout()
        rightcol.addWidget(QLabel("Customize Quick Access Toolbar:"))
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["For all documents (default)"])
        rightcol.addWidget(self.scope_combo)
        rowr = QHBoxLayout()
        self.current = QListWidget()
        self.current.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        rowr.addWidget(self.current, 1)
        arrows = QVBoxLayout()
        arrows.addWidget(QPushButton("\u25b2", clicked=lambda: self._move(-1)))
        arrows.addWidget(QPushButton("\u25bc", clicked=lambda: self._move(1)))
        arrows.addStretch(1)
        rowr.addLayout(arrows, 0)
        rightcol.addLayout(rowr, 1)
        panes.addLayout(rightcol, 1)
        root.addLayout(panes, 1)

        # Options row
        opts = QHBoxLayout()
        self.show_qat_cb = QCheckBox("Show Quick Access Toolbar")
        self.show_qat_cb.setChecked(qat.isVisible())
        opts.addWidget(self.show_qat_cb)
        opts.addWidget(QLabel("Toolbar Position:"))
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["Above Ribbon", "Below Ribbon"])
        self.pos_combo.setCurrentText(
            "Below Ribbon" if qat.position == "below" else "Above Ribbon")
        opts.addWidget(self.pos_combo)
        self.labels_cb = QCheckBox("Always show command labels")
        self.labels_cb.setChecked(qat.show_labels)
        opts.addWidget(self.labels_cb)
        opts.addStretch(1)
        root.addLayout(opts)

        # Reset / Import-Export
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Customizations:"))
        self.reset_combo = QComboBox()
        self.reset_combo.addItems(["Reset only Quick Access Toolbar",
                                   "Remove All Custom Commands"])
        row2.addWidget(self.reset_combo)
        row2.addWidget(QPushButton("Reset...", clicked=self._reset))
        row2.addStretch(1)
        row2.addWidget(QPushButton("Import / Export", clicked=self._import_export))
        root.addLayout(row2)

        # OK / Cancel
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(QPushButton("OK", clicked=self._apply))
        btns.addWidget(QPushButton("Cancel", clicked=self.reject))
        root.addLayout(btns)

        self._populate_available()
        self._refresh_current()

    # -- population ---------------------------------------------------
    def _filtered(self):
        sel = self.choose_combo.currentText()
        if sel == "Popular Commands":
            return [FEATURES[f] for f in POPULAR if f in FEATURES]
        if sel == "All Commands":
            return list(_CATALOG)
        return [c for c in _CATALOG if c.category == sel]

    def _populate_available(self):
        self.available.clear()
        for cmd in self._filtered():
            item = QListWidgetItem(f"{cmd.icon}  {cmd.label}", self.available)
            item.setData(Qt.ItemDataRole.UserRole, cmd.fid)

    def _refresh_current(self):
        row = self.current.currentRow()
        self.current.clear()
        for fid in self._ordered:
            cmd = FEATURES[fid]
            QListWidgetItem(f"{cmd.icon} {cmd.label}", self.current)
        if self.current.count():
            self.current.setCurrentRow(max(0, min(row, self.current.count() - 1)))

    # -- actions ------------------------------------------------------
    def _add(self):
        it = self.available.currentItem()
        if not it:
            return
        fid = it.data(Qt.ItemDataRole.UserRole)
        if fid not in self._ordered:
            self._ordered.append(fid)
            self._refresh_current()

    def _remove(self):
        i = self.current.currentRow()
        if 0 <= i < len(self._ordered):
            self._ordered.pop(i)
            self._refresh_current()

    def _move(self, direction):
        i = self.current.currentRow()
        j = i + direction
        if i < 0 or not (0 <= j < len(self._ordered)):
            return
        self._ordered[i], self._ordered[j] = self._ordered[j], self._ordered[i]
        self._refresh_current()
        self.current.setCurrentRow(j)

    def _reset(self):
        self._ordered = list(DEFAULT_ITEMS)
        self._refresh_current()

    def _import_export(self):
        choice, ok = QInputDialog.getItem(
            self, "Import / Export", "Action:",
            ["Export current settings\u2026", "Import settings\u2026"], 0, False)
        if not ok:
            return
        position = "below" if self.pos_combo.currentText().startswith("Below") else "above"
        if choice.startswith("Export"):
            path, _ = QFileDialog.getSaveFileName(self, "Export QAT settings",
                                                  "qat.json", "JSON (*.json)")
            if path:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump({"items": self._ordered,
                                   "labels": self.labels_cb.isChecked(),
                                   "position": position}, f,
                                  ensure_ascii=False, indent=2)
                except Exception as e:  # noqa: BLE001
                    QMessageBox.warning(self, "Export failed", str(e))
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Import QAT settings",
                                                  "", "JSON (*.json)")
            if path:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._ordered = [x for x in data.get("items", []) if x in FEATURES]
                    self.labels_cb.setChecked(bool(data.get("labels", False)))
                    self.pos_combo.setCurrentText(
                        "Below Ribbon" if data.get("position") == "below" else "Above Ribbon")
                    self._refresh_current()
                except Exception as e:  # noqa: BLE001
                    QMessageBox.warning(self, "Import failed", str(e))

    def _apply(self):
        if not self._ordered:
            QMessageBox.warning(self, "Quick Access Toolbar",
                                "Add at least one command.")
            return
        position = "below" if self.pos_combo.currentText().startswith("Below") else "above"
        self.qat.set_items(self._ordered,
                           labels=self.labels_cb.isChecked(),
                           position=position)
        self.qat.setVisible(self.show_qat_cb.isChecked())
        self.accept()
