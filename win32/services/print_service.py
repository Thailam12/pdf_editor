import os
import pymupdf
from PIL import Image
import io


class PrintService:
    def __init__(self, editor):
        self.editor = editor
        self._settings = {
            "printer": "default",
            "copies": 1,
            "duplex": False,
            "color_mode": "color",
            "paper_size": "A4",
            "orientation": "portrait",
            "page_scaling": "fit",
            "margin": 36
        }

    def print_current_page(self):
        """Print the currently displayed page."""
        try:
            page_num = getattr(self.editor, 'current_page', 0)
            self.print_range(page_num, page_num)
        except Exception as e:
            raise RuntimeError(f"Cannot print current page: {e}")

    def print_all_pages(self):
        """Print all pages in the document."""
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.print_range(0, len(doc) - 1)
        except Exception as e:
            raise RuntimeError(f"Cannot print all pages: {e}")

    def print_range(self, start, end):
        """Print a range of pages from start to end (inclusive)."""
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            start = max(0, start)
            end = min(len(doc) - 1, end)
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                import subprocess
                temp_dir = os.path.join(os.environ.get("TEMP", "."), "pdf_editor_print")
                os.makedirs(temp_dir, exist_ok=True)
                temp_pdf = os.path.join(temp_dir, "print_temp.pdf")
                new_doc = pymupdf.open()
                for i in range(start, end + 1):
                    new_doc.insert_pdf(doc, from_page=i, to_page=i)
                new_doc.save(temp_pdf)
                new_doc.close()
                os.startfile(temp_pdf, "print")
                root.destroy()
            except Exception:
                pass
        except Exception as e:
            raise RuntimeError(f"Cannot print range: {e}")

    def print_booklet(self, input_path, output_path):
        """Create a booklet layout from a PDF (4 pages per sheet, folded)."""
        try:
            doc = pymupdf.open(input_path)
            total_pages = len(doc)
            new_doc = pymupdf.open()
            sheet_count = (total_pages + 3) // 4
            for sheet in range(sheet_count):
                page1_idx = sheet * 2
                page2_idx = sheet * 2 + 1
                page3_idx = total_pages - 1 - (sheet * 2 + 1)
                page4_idx = total_pages - 1 - (sheet * 2)
                blank = new_doc.new_page(width=doc[0].rect.width, height=doc[0].rect.height)
                rect = blank.rect
                half_w = rect.width / 2
                if page1_idx < total_pages:
                    self._insert_page_content(new_doc, blank, doc[page1_idx], 0, 0, half_w, rect.height)
                if page4_idx >= 0 and page4_idx < total_pages:
                    self._insert_page_content(new_doc, blank, doc[page4_idx], half_w, 0, half_w, rect.height)
                page_b = new_doc.new_page(width=rect.width, height=rect.height)
                if page3_idx >= 0 and page3_idx < total_pages:
                    self._insert_page_content(new_doc, page_b, doc[page3_idx], 0, 0, half_w, rect.height)
                if page2_idx < total_pages:
                    self._insert_page_content(new_doc, page_b, doc[page2_idx], half_w, 0, half_w, rect.height)
            new_doc.save(output_path)
            new_doc.close()
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"Cannot create booklet: {e}")

    def print_poster(self, input_path, output_path, rows, cols):
        """Create a poster layout splitting one page across multiple sheets."""
        try:
            doc = pymupdf.open(input_path)
            if len(doc) == 0:
                doc.close()
                return False
            src_page = doc[0]
            src_rect = src_page.rect
            cell_w = src_rect.width
            cell_h = src_rect.height
            new_doc = pymupdf.open()
            poster_page = new_doc.new_page(
                width=cell_w * cols,
                height=cell_h * rows
            )
            for row in range(rows):
                for col in range(cols):
                    pix = src_page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                    img_data = pix.tobytes("png")
                    target_rect = pymupdf.Rect(
                        col * cell_w, row * cell_h,
                        (col + 1) * cell_w, (row + 1) * cell_h
                    )
                    poster_page.insert_image(target_rect, stream=img_data)
            new_doc.save(output_path)
            new_doc.close()
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"Cannot create poster: {e}")

    def get_printer_settings(self):
        """Return current printer settings dict."""
        return dict(self._settings)

    def set_printer_settings(self, settings):
        """Update printer settings."""
        try:
            self._settings.update(settings)
        except Exception as e:
            raise RuntimeError(f"Cannot set printer settings: {e}")

    def preview_page(self, page_num):
        """Return a PIL Image preview of a page for print preview."""
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return None
            page = doc[page_num]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return img
        except Exception:
            return None

    def _insert_page_content(self, target_doc, target_page, src_page, x, y, w, h):
        """Insert source page content into target at given position."""
        try:
            pix = src_page.get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False)
            img_data = pix.tobytes("png")
            rect = pymupdf.Rect(x, y, x + w, y + h)
            target_page.insert_image(rect, stream=img_data)
        except Exception:
            pass
