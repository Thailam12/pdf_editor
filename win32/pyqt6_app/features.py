# -*- coding: utf-8 -*-
"""PyQt6 feature layer: menus + parameter dialogs that drive the services.

Every action here simply collects inputs with native Qt dialogs and calls the
reused service exposed by the :class:`EditorFacade`. Service feedback flows
back through the facade (status bar) and the tkinter→Qt bridge (message boxes).
"""
from __future__ import annotations

import os

import pymupdf
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog, QFileDialog, QInputDialog, QMenu, QMessageBox,
)


class FeatureActions:
    def __init__(self, window):
        self.window = window
        self.controller = window.controller
        self.facade = window.facade

    # ------------------------------------------------------------------
    # small helpers
    # ------------------------------------------------------------------
    def _require(self):
        if not self.controller.has_document:
            QMessageBox.information(self.window, "No document",
                                    "Open a PDF document first.")
            return False
        return True

    def _text(self, title, label, default=""):
        val, ok = QInputDialog.getText(self.window, title, label, text=default)
        return val if ok else None

    def _int(self, title, label, default=0, lo=-1000000, hi=1000000):
        val, ok = QInputDialog.getInt(self.window, title, label, default, lo, hi)
        return val if ok else None

    def _float(self, title, label, default=0.0):
        val, ok = QInputDialog.getDouble(self.window, title, label, default,
                                         -1e9, 1e9, 3)
        return val if ok else None

    def _choice(self, title, label, options):
        val, ok = QInputDialog.getItem(self.window, title, label, options, 0, False)
        return val if ok else None

    def _page(self, label="Page (1-based):", default=None):
        d = (self.controller.current_page + 1) if default is None else default
        n = self._int("Go to page", label, d, 1, max(1, self.controller.total_pages))
        return None if n is None else n - 1

    def _info(self, title, text):
        QMessageBox.information(self.window, title, str(text))

    def _run(self, fn, *args, **kwargs):
        """Call a service method, surface exceptions without crashing."""
        try:
            result = fn(*args, **kwargs)
            self.window.canvas.refresh()
            self.window._refresh_elements()
            return result
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self.window, "Operation failed", str(e))
            return None

    # ==================================================================
    # Page / organize
    # ==================================================================
    def merge_pdfs(self):
        if not self._require():
            return
        paths, _ = QFileDialog.getOpenFileNames(self.window, "Merge PDFs into document",
                                                "", "PDF Files (*.pdf)")
        if paths:
            self._run(self.facade.page_service.merge_pdfs, list(paths))

    def split_pdf(self):
        if not self._require():
            return
        raw = self._text("Split PDF", "Page ranges (e.g. 1-3,4-7):", "1-1")
        if not raw:
            return
        ranges = []
        for part in raw.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                ranges.append((int(a) - 1, int(b) - 1))
            elif part:
                p = int(part) - 1
                ranges.append((p, p))
        if ranges:
            self._run(self.facade.page_service.split_pdf, ranges)

    def duplicate_page(self):
        if not self._require():
            return
        p = self._page()
        if p is not None:
            self._run(self.facade.page_service.duplicate_page, p)

    def add_page(self):
        if not self._require():
            return
        p = self._page()
        if p is not None:
            self._run(self.facade.page_service.add_page, p)

    def delete_page(self):
        if not self._require():
            return
        p = self._page()
        if p is not None:
            self._run(self.facade.page_service.delete_page, p)

    def move_page(self):
        if not self._require():
            return
        src = self._int("Move page", "Move page (1-based):", 1, 1, self.controller.total_pages)
        if src is None:
            return
        dst = self._int("Move page", "To position (1-based):", 1, 1, self.controller.total_pages)
        if dst is not None:
            self._run(self.facade.page_service.move_page, src - 1, dst - 1)

    def rotate_page(self):
        if not self._require():
            return
        p = self._page()
        if p is None:
            return
        angle = self._choice("Rotate page", "Angle:", ["90", "180", "270"])
        if angle:
            self._run(self.facade.page_service.rotate_page, p, int(angle))

    def crop_page(self):
        if not self._require():
            return
        p = self._page()
        if p is None:
            return
        x = self._float("Crop", "X:", 0.0)
        y = self._float("Crop", "Y:", 0.0)
        w = self._float("Crop", "Width:", 595.0)
        h = self._float("Crop", "Height:", 842.0)
        if None not in (x, y, w, h):
            self._run(self.facade.page_service.crop_page, p, x, y, w, h)

    def resize_page(self):
        if not self._require():
            return
        p = self._page()
        if p is None:
            return
        w = self._float("Resize", "Width (pt):", 595.0)
        h = self._float("Resize", "Height (pt):", 842.0)
        if None not in (w, h):
            self._run(self.facade.page_service.resize_page, p, w, h)

    # ==================================================================
    # Watermark
    # ==================================================================
    def add_text_watermark(self):
        if not self._require():
            return
        text = self._text("Text watermark", "Watermark text:", "DRAFT")
        if not text:
            return
        color = self._pick_color("#888888")
        svc = self.facade.watermark_service
        self._run(svc.add_text_watermark, text, self.controller.current_page,
                  60, color or "#888888", 0.3, 45)

    def add_image_watermark(self):
        if not self._require():
            return
        path, _ = QFileDialog.getOpenFileName(self.window, "Watermark image", "",
                                              "Images (*.png *.jpg *.jpeg)")
        if path:
            self._run(self.facade.watermark_service.add_image_watermark,
                      path, self.controller.current_page, 0.3, 1.0)

    def remove_watermarks(self):
        if not self._require():
            return
        self._run(self.facade.watermark_service.remove_watermarks)

    # ==================================================================
    # Bates numbering
    # ==================================================================
    def bates_all_pages(self):
        if not self._require():
            return
        prefix = self._text("Bates numbering", "Prefix:", "BATES-")
        if prefix is None:
            return
        start = self._int("Bates numbering", "Start number:", 1, 0, 10 ** 9) or 1
        self._run(self.facade.bates_service.add_bates_all_pages, prefix, start)

    def bates_remove(self):
        if not self._require():
            return
        self._run(self.facade.bates_service.remove_bates_numbers)

    # ==================================================================
    # Header / footer
    # ==================================================================
    def add_page_numbers(self):
        if not self._require():
            return
        pos = self._choice("Page numbers", "Position:", [
            "footer-center", "footer-left", "footer-right",
            "header-center", "header-left", "header-right"]) or "footer-center"
        self._run(self.facade.header_footer_service.add_page_numbers, pos)

    def add_text_header(self):
        if not self._require():
            return
        text = self._text("Header text", "Header text:")
        if text:
            self._run(self.facade.header_footer_service.add_text_header,
                      text, "header-center")

    def add_date_stamp(self):
        if not self._require():
            return
        self._run(self.facade.header_footer_service.add_date_stamp, "footer-right")

    def remove_headers_footers(self):
        if not self._require():
            return
        self._run(self.facade.header_footer_service.remove_headers_footers)

    # ==================================================================
    # Links
    # ==================================================================
    def add_link(self):
        if not self._require():
            return
        url = self._text("Add link", "URL:", "https://")
        if not url:
            return
        svc = self.facade.link_service
        self._run(svc.add_link, 72, 72, 120, 20, url)

    def add_page_link(self):
        if not self._require():
            return
        target = self._page("Target page (1-based):", 1)
        if target is not None:
            self._run(self.facade.link_service.add_page_link, 72, 72, 120, 20, target)

    # ==================================================================
    # Forms
    # ==================================================================
    def detect_form_fields(self):
        if not self._require():
            return
        fields = self._run(self.facade.form_service.detect_form_fields,
                           self.controller.current_page)
        self._info("Form fields", fields or "No form fields found.")

    def get_form_data(self):
        if not self._require():
            return
        data = self._run(self.facade.form_service.get_form_data)
        self._info("Form data", data or "No form data.")

    # ==================================================================
    # Redaction
    # ==================================================================
    def mark_redaction(self):
        if not self._require():
            return
        svc = self.facade.redaction_service
        x = self._float("Redaction", "X:", 72.0)
        y = self._float("Redaction", "Y:", 72.0)
        w = self._float("Redaction", "Width:", 200.0)
        h = self._float("Redaction", "Height:", 30.0)
        if None not in (x, y, w, h):
            self._run(svc.mark_for_redaction, x, y, w, h)

    def apply_redactions(self):
        if not self._require():
            return
        self._run(self.facade.redaction_service.apply_redactions)

    # ==================================================================
    # Search & replace
    # ==================================================================
    def find_text(self):
        if not self._require():
            return
        query = self._text("Find", "Search text:")
        if not query:
            return
        results = self.facade.search_service.search_text(query)
        if not results:
            self._info("Find", f"No matches for “{query}”.")
            return
        items = [f"Page {r['page'] + 1}: {r['text'][:60]}" for r in results]
        pick, ok = QInputDialog.getItem(self.window, f"{len(results)} matches",
                                        "Jump to result:", items, 0, False)
        if ok and pick:
            page = int(pick.split("Page ", 1)[1].split(":", 1)[0]) - 1
            self.controller.set_current_page(page)

    def replace_text(self):
        if not self._require():
            return
        query = self._text("Replace", "Find text:")
        if not query:
            return
        repl = self._text("Replace", "Replace with:")
        if repl is None:
            return
        count = self._run(self.facade.search_service.replace_text, query, repl)
        if count is not None:
            self._info("Replace", f"Replaced {count} occurrence(s).")

    # ==================================================================
    # Compress / optimize
    # ==================================================================
    def compress(self):
        if not self._require() or not self.controller.path:
            return
        level = self._choice("Compress PDF", "Compression level:",
                             ["low", "medium", "high"]) or "medium"
        out, _ = QFileDialog.getSaveFileName(self.window, "Save compressed PDF",
                                             _suffixed(self.controller.path, f"_compressed_{level}"),
                                             "PDF Files (*.pdf)")
        if out:
            self._run(self.facade.compress_service.compress, self.controller.path, out, level)
            self._info("Compress", f"Saved compressed copy to\n{out}")

    # ==================================================================
    # Compare
    # ==================================================================
    def compare(self):
        if not self._require() or not self.controller.path:
            return
        other, _ = QFileDialog.getOpenFileName(self.window, "Compare with PDF",
                                               "", "PDF Files (*.pdf)")
        if not other:
            return
        out, _ = QFileDialog.getSaveFileName(self.window, "Save comparison image",
                                             _suffixed(self.controller.path, "_compare.png"),
                                             "PNG Image (*.png)")
        if not out:
            return
        saved = self._run(self.facade.compare_service.compare_files,
                          self.controller.path, other, out)
        if saved:
            changes = self.facade.compare_service.get_text_changes()
            self._info("Compare",
                       f"Diff image saved to\n{saved}\n\n"
                       f"{len(changes)} text change(s) detected.")

    # ==================================================================
    # Security
    # ==================================================================
    def set_password(self):
        if not self._require():
            return
        pw = self._text("Encrypt", "Password:")
        if not pw:
            return
        self._run(self.facade.security_service.set_password, pw, pw)

    def remove_password(self):
        if not self._require():
            return
        pw = self._text("Decrypt", "Password:")
        if pw is not None:
            self._run(self.facade.security_service.remove_password, pw)

    # ==================================================================
    # Export
    # ==================================================================
    def export_images(self):
        if not self._require():
            return
        out_dir = QFileDialog.getExistingDirectory(self.window, "Export pages as images")
        if not out_dir:
            return
        fmt = self._choice("Export", "Format:", ["png", "jpg"]) or "png"
        dpi = self._int("Export", "DPI:", 200, 72, 600) or 200
        self._run(self.facade.export_service.export_to_images, out_dir, fmt, dpi)

    def export_docx(self):
        if not self._require() or not self.controller.path:
            return
        out, _ = QFileDialog.getSaveFileName(self.window, "Export to DOCX",
                                             _suffixed(self.controller.path, ".docx"),
                                             "Word Document (*.docx)")
        if out:
            self._run(self.facade.export_service.export_to_docx, out)

    def export_html(self):
        if not self._require() or not self.controller.path:
            return
        out, _ = QFileDialog.getSaveFileName(self.window, "Export to HTML",
                                             _suffixed(self.controller.path, ".html"),
                                             "HTML (*.html)")
        if out:
            self._run(self.facade.export_service.export_to_html, out)

    # ==================================================================
    # AI assistant
    # ==================================================================
    def ai_extract(self):
        if not self._require():
            return
        text = self.facade.ai_service.extract_text(self.controller.current_page) \
            if self.facade.service("ai_service") else \
            self.controller.page().get_text("text")
        self._info("Extracted text", text or "(empty page)")

    def ai_summarize(self):
        if not self._require():
            return
        page_text = self.controller.page().get_text("text").strip()
        summary = self.facade.ai_service.summarize_text(page_text)
        self._info("Summary", summary or "(nothing to summarize)")

    def ai_translate(self):
        text = self._text("Translate", "Text to translate:")
        if not text:
            return
        lang = self._choice("Translate", "Target language:", ["vi", "en"]) or "vi"
        self._info("Translation", self.facade.ai_service.translate_text(text, lang))

    def ai_analyze(self):
        if not self._require():
            return
        stats = self.facade.ai_service.analyze_document()
        self._info("Document analysis", stats)

    # ==================================================================
    # TTS
    # ==================================================================
    def tts_page(self):
        if not self._require():
            return
        self._run(self.facade.tts_service.speak_page, self.controller.current_page)

    def tts_stop(self):
        if self.facade.tts_service:
            self._run(self.facade.tts_service.stop)

    # ==================================================================
    # Measurement
    # ==================================================================
    def measure_distance(self):
        if not self._require():
            return
        x1 = self._float("Measure", "x1:", 0.0)
        y1 = self._float("Measure", "y1:", 0.0)
        x2 = self._float("Measure", "x2:", 100.0)
        y2 = self._float("Measure", "y2:", 100.0)
        if None not in (x1, y1, x2, y2):
            d = self.facade.measurement_service.measure_distance(x1, y1, x2, y2)
            self._info("Distance", d)

    # ==================================================================
    # PDF/A + Accessibility validation
    # ==================================================================
    def validate_pdfa(self):
        if not self._require() or not self.controller.path:
            return
        result = self.facade.pdfa_service.validate_pdfa(self.controller.path)
        self._info("PDF/A validation", result)

    def check_accessibility(self):
        if not self._require() or not self.controller.path:
            return
        result = self.facade.accessibility_service.check_accessibility(self.controller.path)
        self._info("Accessibility report", result)

    # ==================================================================
    # Spellcheck
    # ==================================================================
    def spellcheck_page(self):
        if not self._require():
            return
        text = self.controller.page().get_text("text")
        issues = self.facade.spellcheck_service.check_text(text)
        self._info("Spellcheck", issues or "No issues found.")

    # ==================================================================
    # Background
    # ==================================================================
    def set_background(self):
        if not self._require():
            return
        color = self._pick_color("#ffffff")
        if color:
            self._run(self.facade.background_service.set_solid_background,
                      self.controller.current_page, color)

    # ==================================================================
    # Bookmarks
    # ==================================================================
    def add_bookmark(self):
        if not self._require():
            return
        title = self._text("Bookmark", "Title:")
        if not title:
            return
        self._run(self.facade.bookmark_service.add_bookmark,
                  title, self.controller.current_page)

    def list_bookmarks(self):
        if not self._require():
            return
        bms = self.facade.bookmark_service.get_bookmarks()
        if not bms:
            self._info("Bookmarks", "No bookmarks.")
            return
        items = [str(b) for b in bms]
        pick, ok = QInputDialog.getItem(self.window, "Bookmarks", "Jump to:", items, 0, False)
        if ok and pick:
            idx = items.index(pick)
            b = bms[idx]
            page = b.get("page", 0) if isinstance(b, dict) else getattr(b, "page", 0)
            self.controller.set_current_page(page)

    # ==================================================================
    # OCR (native Qt — the legacy tkinter OCR was non-functional)
    # ==================================================================
    def run_ocr(self):
        if not self._require():
            return
        lang = self._choice("OCR", "Language:", ["eng", "vie"]) or "eng"
        scope = self._choice("OCR", "Scope:", ["Current page", "All pages"])
        if scope is None:
            return
        all_pages = scope.startswith("All")
        from win32.ocr_utils import (
            ocr_page_to_boxes, boxes_to_editor_text_elements, OCRBox,
        )
        from win32.models.elements import elements_from_tuples
        try:
            from PIL import Image
        except ImportError:
            QMessageBox.critical(self.window, "OCR", "Pillow is required for OCR.")
            return
        doc = self.controller.doc
        pages = range(len(doc)) if all_pages else [self.controller.current_page]
        total = 0
        for p in pages:
            page = doc[p]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            boxes = ocr_page_to_boxes(img, lang=lang)
            tuples = boxes_to_editor_text_elements(
                [OCRBox(b.text, b.x1_px, b.y1_px, b.x2_px, b.y2_px) for b in boxes],
                p, pix.width, pix.height,
                float(page.rect.width), float(page.rect.height),
            )
            els = elements_from_tuples(tuples)
            self.controller.elements.extend(els)
            total += len(els)
        self.controller.set_modified(True)
        self.window.canvas.refresh()
        self.window._refresh_elements()
        self._info("OCR", f"Recognized {total} text element(s).")

    # ==================================================================
    def _pick_color(self, default="#000000"):
        chosen = QColorDialog.getColor(QColor(default), self.window, "Choose color")
        return chosen.name() if chosen.isValid() else None


def _suffixed(path, suffix):
    base, ext = os.path.splitext(path)
    if suffix.startswith("."):
        return base + suffix
    return base + suffix + (ext or ".pdf")


def build_menus(window):
    """Populate the Tools/advanced menus on the main window."""
    fa = FeatureActions(window)
    window.features = fa
    mb = window.menuBar()
    menus = {m.title(): m for m in mb.findChildren(QMenu)}

    # --- Page submenu additions -------------------------------------
    m_page = menus.get("&Page")
    if m_page:
        m_page.addSeparator()
        m_page.addAction("Merge PDFs…", fa.merge_pdfs)
        m_page.addAction("Split PDF…", fa.split_pdf)
        m_page.addAction("Duplicate Page", fa.duplicate_page)
        m_page.addAction("Move Page…", fa.move_page)
        m_page.addAction("Add Page After…", fa.add_page)
        m_page.addAction("Crop Page…", fa.crop_page)
        m_page.addAction("Resize Page…", fa.resize_page)

    # --- Tools ------------------------------------------------------
    tools = mb.addMenu("&Tools")
    tools.addAction("Find Text…", fa.find_text)
    tools.addAction("Replace…", fa.replace_text)
    tools.addSeparator()
    tools.addAction("Compress PDF…", fa.compress)
    tools.addAction("Compare with PDF…", fa.compare)
    tools.addAction("Validate PDF/A…", fa.validate_pdfa)
    tools.addAction("Check Accessibility…", fa.check_accessibility)
    tools.addAction("Spellcheck Page…", fa.spellcheck_page)

    # --- Organize (watermark/bates/header) --------------------------
    org = mb.addMenu("&Organize")
    org.addAction("Text Watermark…", fa.add_text_watermark)
    org.addAction("Image Watermark…", fa.add_image_watermark)
    org.addAction("Remove Watermarks", fa.remove_watermarks)
    org.addSeparator()
    org.addAction("Bates Numbering (all pages)…", fa.bates_all_pages)
    org.addAction("Remove Bates Numbers", fa.bates_remove)
    org.addSeparator()
    org.addAction("Add Page Numbers…", fa.add_page_numbers)
    org.addAction("Add Header Text…", fa.add_text_header)
    org.addAction("Add Date Stamp", fa.add_date_stamp)
    org.addAction("Remove Headers/Footers", fa.remove_headers_footers)
    org.addSeparator()
    org.addAction("Set Page Background…", fa.set_background)

    # --- Insert extras ----------------------------------------------
    ins = menus.get("&Insert")
    if ins:
        ins.addSeparator()
        ins.addAction("Hyperlink…", fa.add_link)
        ins.addAction("Page Link…", fa.add_page_link)
        ins.addSeparator()
        ins.addAction("Detect Form Fields…", fa.detect_form_fields)
        ins.addAction("Show Form Data", fa.get_form_data)
        ins.addSeparator()
        ins.addAction("Mark Redaction…", fa.mark_redaction)
        ins.addAction("Apply Redactions", fa.apply_redactions)
        ins.addSeparator()
        ins.addAction("Add Bookmark…", fa.add_bookmark)

    # --- Protect ----------------------------------------------------
    protect = mb.addMenu("&Protect")
    protect.addAction("Encrypt (set password)…", fa.set_password)
    protect.addAction("Decrypt (remove password)…", fa.remove_password)

    # --- Convert / Export -------------------------------------------
    conv = mb.addMenu("Con&vert")
    conv.addAction("Export to Images…", fa.export_images)
    conv.addAction("Export to DOCX…", fa.export_docx)
    conv.addAction("Export to HTML…", fa.export_html)
    conv.addSeparator()
    conv.addAction("Measure Distance…", fa.measure_distance)

    # --- AI / OCR ---------------------------------------------------
    ai = mb.addMenu("&AI")
    ai.addAction("Extract Text", fa.ai_extract)
    ai.addAction("Summarize Page", fa.ai_summarize)
    ai.addAction("Translate…", fa.ai_translate)
    ai.addAction("Analyze Document", fa.ai_analyze)
    ai.addSeparator()
    ai.addAction("OCR (recognize text)…", fa.run_ocr)
    ai.addSeparator()
    ai.addAction("Read Page Aloud", fa.tts_page)
    ai.addAction("Stop Reading", fa.tts_stop)
    return fa
