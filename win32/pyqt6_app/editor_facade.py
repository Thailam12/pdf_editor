# -*- coding: utf-8 -*-
"""PyQt6 facade exposing the ``editor`` interface the logic services expect.

The ~30 reusable services (page, search, compare, export, security, watermark,
bates, …) were written against the legacy tkinter editor. They only touch a
small, well-defined contract:

    editor.pdf_utils / editor.elements / editor.current_page /
    editor.total_pages / editor.current_pdf / editor.selected_element /
    editor.zoom_level / editor.is_temp_document / editor.element_images /
    editor.stamp_elements / editor.undo_manager (save_state/clear/undo/redo) /
    editor.status.configure(text=...) / editor.canvas_manager.update_preview() /
    editor.update_info_panel() / editor.root / <peer>_service

This facade implements that contract on top of the Qt ``DocumentController``
and ``MainWindow``, so every service keeps working — reused, not rewritten.
"""
from __future__ import annotations

from PyQt6.QtCore import QTimer


class _StatusShim:
    """Mimics the tkinter status ``Label`` (only ``configure(text=...)``)."""

    def __init__(self, window):
        self._window = window

    def configure(self, **kw):
        text = kw.get("text")
        if text is not None:
            self._window._set_status(str(text))

    # tkinter also allows config(...)
    config = configure

    def cget(self, key):
        return ""


class _CanvasManagerShim:
    """Mimics the tkinter canvas_manager: services only call update_preview()."""

    def __init__(self, facade):
        self._facade = facade

    def update_preview(self):
        self._facade.refresh()

    def redraw(self):
        self._facade.refresh()


class _CanvasPreviewShim:
    """Minimal stand-in for the tkinter canvas (size queries only)."""

    def __init__(self, controller):
        self._controller = controller

    def winfo_width(self):
        return 800

    def winfo_height(self):
        return 1000

    def winfo_rootx(self):
        return 0

    def winfo_rooty(self):
        return 0


class _RootShim:
    """Mimics the tkinter root for ``.after`` scheduling used by services."""

    def __init__(self, window):
        self._window = window

    def after(self, ms, func=None, *args):
        if func is None:
            return
        QTimer.singleShot(max(0, int(ms)), lambda: func(*args))

    def after_idles(self, func, *args):
        self.after(1, func, *args)

    def update_idletasks(self):
        pass

    # clipboard passthrough (used only by legacy interaction code paths)
    def clipboard_clear(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().clear()

    def clipboard_append(self, text):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(str(text))


class _UndoAdapter:
    """Maps the tkinter undo_manager API onto DocumentController."""

    def __init__(self, controller):
        self._c = controller

    def save_state(self, elements=None):
        self._c._push_undo()

    def clear(self):
        self._c._undo_stack.clear()
        self._c._redo_stack.clear()
        self._c._emit_undo_state()

    def undo(self, current_elements=None):
        self._c.undo()
        return self._c.elements

    def redo(self, current_elements=None):
        self._c.redo()
        return self._c.elements

    def can_undo(self):
        return bool(self._c._undo_stack)

    def can_redo(self):
        return bool(self._c._redo_stack)


class EditorFacade:
    def __init__(self, controller, window):
        self.controller = controller
        self.window = window

        # Editor-contract objects.
        self.pdf_utils = controller.pdf_utils
        self.status = _StatusShim(window)
        self.canvas_manager = _CanvasManagerShim(self)
        self.canvas_preview = _CanvasPreviewShim(controller)
        self.undo_manager = _UndoAdapter(controller)
        self.root = _RootShim(window)

        # Extra mutable state some services expect.
        self.element_images = []
        self.stamp_elements = []
        self.is_temp_document = False

        self._services = {}
        self._register_services()

    # ------------------------------------------------------------------
    # editor.* state, mapped onto the controller
    # ------------------------------------------------------------------
    @property
    def elements(self):
        return self.controller.elements

    @elements.setter
    def elements(self, value):
        self.controller.elements = list(value)

    @property
    def current_pdf(self):
        return self.controller.path

    @current_pdf.setter
    def current_pdf(self, value):
        self.controller.path = value

    @property
    def current_page(self):
        return self.controller.current_page

    @current_page.setter
    def current_page(self, value):
        self.controller.current_page = max(0, int(value))

    @property
    def total_pages(self):
        return self.controller.total_pages

    @total_pages.setter
    def total_pages(self, value):
        self.controller.total_pages = int(value)

    @property
    def selected_element(self):
        return self.controller.selected_element()

    @selected_element.setter
    def selected_element(self, value):
        if value is None:
            self.controller.select(None)
        else:
            try:
                idx = self.controller.elements.index(value)
                self.controller.select(idx)
            except ValueError:
                pass

    @property
    def zoom_level(self):
        return self.controller.zoom / 100.0

    @zoom_level.setter
    def zoom_level(self, value):
        self.controller.set_zoom(int(round(float(value) * 100)))

    # ------------------------------------------------------------------
    # Lifecycle helpers used by services
    # ------------------------------------------------------------------
    def update_info_panel(self):
        self.window._refresh_elements()

    def refresh(self):
        """Re-pull page count from the (possibly mutated) doc and repaint."""
        doc = self.controller.doc
        if doc is not None:
            try:
                self.controller.total_pages = len(doc)
            except Exception:
                pass
        if self.controller.current_page >= self.controller.total_pages:
            self.controller.current_page = max(0, self.controller.total_pages - 1)
        self.controller.set_modified(True)
        self.window.page_list.reload_pages()
        self.window.canvas.refresh()
        self.window._refresh_elements()
        self.window._update_actions()

    # ------------------------------------------------------------------
    # Service registration (reused tkinter-independent logic services)
    # ------------------------------------------------------------------
    def _register_services(self):
        from win32.services.page_service import PageService
        from win32.services.search_service import SearchService
        from win32.services.export_service import ExportService
        from win32.services.security_service import SecurityService
        from win32.services.watermark_service import WatermarkService
        from win32.services.bookmark_service import BookmarkService
        from win32.services.redaction_service import RedactionService
        from win32.services.compare_service import CompareService
        from win32.services.compress_service import CompressService
        from win32.services.header_footer_service import HeaderFooterService
        from win32.services.link_service import LinkService
        from win32.services.form_service import FormService
        from win32.services.measurement_service import MeasurementService
        from win32.services.bates_service import BatesService
        from win32.services.pdfa_service import PdfAService
        from win32.services.spellcheck_service import SpellCheckService
        from win32.services.tts_service import TextToSpeechService
        from win32.services.accessibility_service import AccessibilityService
        from win32.services.background_service import BackgroundService
        from win32.services.article_service import ArticleService
        from win32.services.automation_service import AutomationService
        from win32.services.index_service import IndexService
        from win32.services.snap_service import SnapService
        from win32.services.bookmark_import_service import BookmarkImportService
        from win32.services.ai_service import AIService

        specs = [
            ("page_service", PageService),
            ("search_service", SearchService),
            ("export_service", ExportService),
            ("security_service", SecurityService),
            ("watermark_service", WatermarkService),
            ("bookmark_service", BookmarkService),
            ("redaction_service", RedactionService),
            ("compare_service", CompareService),
            ("compress_service", CompressService),
            ("header_footer_service", HeaderFooterService),
            ("link_service", LinkService),
            ("form_service", FormService),
            ("measurement_service", MeasurementService),
            ("bates_service", BatesService),
            ("pdfa_service", PdfAService),
            ("spellcheck_service", SpellCheckService),
            ("tts_service", TextToSpeechService),
            ("accessibility_service", AccessibilityService),
            ("background_service", BackgroundService),
            ("article_service", ArticleService),
            ("automation_service", AutomationService),
            ("index_service", IndexService),
            ("snap_service", SnapService),
            ("bookmark_import_service", BookmarkImportService),
            ("ai_service", AIService),
        ]
        for name, cls in specs:
            try:
                svc = cls(self)
            except Exception:
                svc = None
            setattr(self, name, svc)
            if svc is not None:
                self._services[name] = svc

    def service(self, name):
        return self._services.get(name)
