import threading
import tkinter as tk
from tkinter import ttk


class OCRManager:
    def __init__(self, editor):
        self.editor = editor

    def ocr_dialog(self, all_pages=False):
        dialog = tk.Toplevel(self.editor.root)
        dialog.title("OCR")
        dialog.geometry("300x120")
        dialog.transient(self.editor.root)
        dialog.grab_set()
        tk.Label(dialog, text="Language:").pack(pady=10)
        v = tk.StringVar(value="en")
        ttk.Combobox(
            dialog, textvariable=v, values=["en", "vi", "ch"], state="readonly"
        ).pack()

        def start():
            dialog.destroy()
            self._start_ocr(all_pages, v.get())

        tk.Button(dialog, text="Start", command=start, bg="#007bff", fg="white").pack(pady=10)

    def _start_ocr(self, all_pages, lang):
        threading.Thread(target=self._worker, args=(all_pages, lang), daemon=True).start()

    def _worker(self, all_pages, lang):
        from win32.ocr_utils import OCRBox, boxes_to_editor_text_elements
        import pymupdf
        from PIL import Image
        from models.elements import elements_from_tuples

        e = self.editor
        pages = range(len(e.pdf_utils.doc)) if all_pages else [e.current_page]

        for p in pages:
            page = e.pdf_utils.doc[p]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            boxes = e._ocr_image_to_boxes(img, lang=lang)
            tuples = boxes_to_editor_text_elements(
                [OCRBox(b.text, b.x1_px, b.y1_px, b.x2_px, b.y2_px) for b in boxes],
                p, pix.width, pix.height,
                float(page.rect.width), float(page.rect.height),
            )
            els = elements_from_tuples(tuples)

            def add_ocr_elements(els=els):
                e.elements.extend(els)
                e.canvas_manager.update_preview()
                e.update_info_panel()

            e.root.after(0, add_ocr_elements)
