# -*- coding: utf-8 -*-
"""Toolkit-agnostic document controller for the PyQt6 editor.

Holds the open PDF (via PyMuPDF), the editable element list, current page,
zoom and an undo/redo stack. Emits Qt signals so the views (canvas, panels)
can react without the model knowing about them.
"""
import os
import json
import copy
import tempfile

import pymupdf
from PyQt6.QtCore import QObject, pyqtSignal

from win32.pdf_utils import PDFUtils
from win32.models.elements import (
    elements_to_json_list, elements_from_json_list,
)


def _sidecar_path(pdf_path):
    return pdf_path + ".elements.json"


class DocumentController(QObject):
    document_loaded = pyqtSignal()
    page_changed = pyqtSignal(int)
    elements_changed = pyqtSignal()
    selection_changed = pyqtSignal(int)
    undo_state_changed = pyqtSignal(bool, bool)
    modified_changed = pyqtSignal(bool)

    MIN_ZOOM = 25
    MAX_ZOOM = 400

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_utils = PDFUtils()
        self.doc = None
        self.path = None
        self.elements = []
        self.current_page = 0
        self.total_pages = 0
        self.zoom = 100  # percent
        self.selected_index = None
        self._undo_stack = []
        self._redo_stack = []
        self._modified = False

    # ------------------------------------------------------------------
    # Loading / saving
    # ------------------------------------------------------------------
    @property
    def has_document(self):
        return self.doc is not None and self.total_pages > 0

    def open(self, path):
        path = os.path.abspath(path)
        self.pdf_utils.load_pdf(path)
        self.doc = self.pdf_utils.doc
        self.path = path
        self.current_page = 0
        self.total_pages = len(self.doc)
        self.elements = []
        saved = self._load_sidecar(path)
        self.elements.extend(saved)
        self.selected_index = None
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.set_modified(False)
        self.document_loaded.emit()
        self.page_changed.emit(self.current_page)
        self.elements_changed.emit()
        self._emit_undo_state()
        return True

    def _load_sidecar(self, path):
        p = _sidecar_path(path)
        if not os.path.exists(p):
            return []
        try:
            with open(p, "r", encoding="utf-8") as f:
                return elements_from_json_list(json.load(f))
        except Exception:
            return []

    def _save_sidecar(self):
        if not self.path:
            return
        try:
            with open(_sidecar_path(self.path), "w", encoding="utf-8") as f:
                json.dump(elements_to_json_list(self.elements), f,
                          ensure_ascii=False, indent=2)
        except Exception:
            pass

    def save(self, path=None):
        if not self.has_document:
            return False
        target = os.path.abspath(path or self.path)
        # Flush page-level operations from the live document first.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            base = tmp.name
        try:
            self.doc.save(base)
            tuples = []
            for elem in self.elements:
                etype, params = elem.to_tuple()
                params = dict(params)
                params["page"] = elem.page
                tuples.append((etype, params))
            self.pdf_utils.save_edited_pdf(base, target, tuples)
        finally:
            try:
                os.remove(base)
            except OSError:
                pass
        # Retarget to the saved file but keep the in-memory editable element
        # list (the live doc still holds only page-level ops, so re-saving is
        # idempotent and elements are never double-baked).
        self.path = target
        self._save_sidecar()
        self.set_modified(False)
        return True

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------
    def page(self, index=None):
        idx = self.current_page if index is None else index
        if not self.has_document or idx < 0 or idx >= self.total_pages:
            return None
        return self.doc[idx]

    def set_current_page(self, index):
        if not self.has_document:
            return
        index = max(0, min(self.total_pages - 1, index))
        if index == self.current_page:
            return
        self.current_page = index
        self.selected_index = None
        self.selection_changed.emit(-1)
        self.page_changed.emit(index)

    def next_page(self):
        self.set_current_page(self.current_page + 1)

    def prev_page(self):
        self.set_current_page(self.current_page - 1)

    def rotate_current(self, degrees=90):
        if not self.has_document:
            return
        self._push_undo()
        page = self.doc[self.current_page]
        page.set_rotation((page.rotation + degrees) % 360)
        self.set_modified(True)
        self.page_changed.emit(self.current_page)

    def delete_current_page(self):
        if not self.has_document or self.total_pages <= 1:
            return
        self._push_undo()
        self.doc.delete_page(self.current_page)
        self.total_pages = len(self.doc)
        self.current_page = min(self.current_page, self.total_pages - 1)
        self.set_modified(True)
        self.document_loaded.emit()
        self.page_changed.emit(self.current_page)

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------
    def set_zoom(self, percent):
        percent = max(self.MIN_ZOOM, min(self.MAX_ZOOM, int(percent)))
        if percent != self.zoom:
            self.zoom = percent
            self.page_changed.emit(self.current_page)

    def zoom_in(self):
        self.set_zoom(self.zoom + 10)

    def zoom_out(self):
        self.set_zoom(self.zoom - 10)

    def zoom_fit(self, view_w, view_h):
        page = self.page()
        if page is None or view_w <= 0 or view_h <= 0:
            return
        rect = page.rect
        if rect.width <= 0 or rect.height <= 0:
            return
        zx = view_w / rect.width * 100
        zy = view_h / rect.height * 100
        self.set_zoom(min(zx, zy))

    # ------------------------------------------------------------------
    # Elements
    # ------------------------------------------------------------------
    def add_element(self, element):
        self._push_undo()
        element.page = self.current_page
        self.elements.append(element)
        self.select(len(self.elements) - 1)
        self.set_modified(True)
        self.elements_changed.emit()

    def remove_selected(self):
        if self.selected_index is None:
            return
        self._push_undo()
        del self.elements[self.selected_index]
        self.selected_index = None
        self.selection_changed.emit(-1)
        self.set_modified(True)
        self.elements_changed.emit()

    def move_selected(self, dx, dy):
        if self.selected_index is None:
            return
        elem = self.elements[self.selected_index]
        self._apply_delta(elem, dx, dy)
        self.set_modified(True)
        self.elements_changed.emit()

    @staticmethod
    def _apply_delta(elem, dx, dy):
        for attr in ("x", "y"):
            if hasattr(elem, attr):
                setattr(elem, attr, getattr(elem, attr) + (dx if attr == "x" else dy))
        for attr in ("x1", "y1", "x2", "y2"):
            if hasattr(elem, attr):
                base = {"x1": dx, "y1": dy, "x2": dx, "y2": dy}[attr]
                setattr(elem, attr, getattr(elem, attr) + base)
        if hasattr(elem, "points") and elem.points:
            elem.points = [(px + dx, py + dy) for px, py in elem.points]

    def select(self, index):
        if index is not None and not (0 <= index < len(self.elements)):
            index = None
        self.selected_index = index
        self.selection_changed.emit(-1 if index is None else index)

    def selected_element(self):
        if self.selected_index is None:
            return None
        return self.elements[self.selected_index]

    def elements_on_current_page(self):
        return [(i, e) for i, e in enumerate(self.elements)
                if e.page == self.current_page]

    # ------------------------------------------------------------------
    # Undo / redo (element snapshots)
    # ------------------------------------------------------------------
    def _push_undo(self):
        self._undo_stack.append(copy.deepcopy(self.elements))
        if len(self._undo_stack) > 100:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._emit_undo_state()

    def undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(copy.deepcopy(self.elements))
        self.elements = self._undo_stack.pop()
        self.selected_index = None
        self.set_modified(True)
        self.selection_changed.emit(-1)
        self.elements_changed.emit()
        self._emit_undo_state()

    def redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(copy.deepcopy(self.elements))
        self.elements = self._redo_stack.pop()
        self.selected_index = None
        self.set_modified(True)
        self.selection_changed.emit(-1)
        self.elements_changed.emit()
        self._emit_undo_state()

    def _emit_undo_state(self):
        self.undo_state_changed.emit(bool(self._undo_stack), bool(self._redo_stack))

    # ------------------------------------------------------------------
    # Modified flag
    # ------------------------------------------------------------------
    def set_modified(self, value):
        if self._modified != value:
            self._modified = value
            self.modified_changed.emit(value)

    def close(self):
        if self.doc is not None:
            try:
                self.doc.close()
            except Exception:
                pass
        self.doc = None
        self.path = None
        self.elements = []
        self.total_pages = 0
        self.current_page = 0
        self.selected_index = None
