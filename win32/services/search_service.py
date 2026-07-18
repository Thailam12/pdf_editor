import pymupdf
from tkinter import messagebox


class SearchService:
    def __init__(self, editor):
        self.editor = editor

    def search_text(self, query, case_sensitive=False, whole_word=False):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or not query:
                return []
            results = []
            flags = 0
            if not case_sensitive:
                flags |= pymupdf.TEXT_PRESERVE_WHITESPACE
            for page_num in range(len(doc)):
                page = doc[page_num]
                spans = page.search_for(query, quads=False)
                for span in spans:
                    if isinstance(span, pymupdf.Rect):
                        text = page.get_text("text", clip=span).strip()
                        if whole_word and text and not self._is_whole_word(query, text):
                            continue
                        results.append({
                            "page": page_num,
                            "x": span.x0,
                            "y": span.y0,
                            "w": span.width,
                            "h": span.height,
                            "text": text or query,
                        })
            return results
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi tìm kiếm: {str(e)}")
            return []

    def _is_whole_word(self, query, text):
        import re
        return bool(re.search(r'\b' + re.escape(query) + r'\b', text))

    def replace_text(self, query, replacement, case_sensitive=False):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or not query:
                return 0
            self.editor.undo_manager.save_state(self.editor.elements)
            count = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                spans = page.search_for(query, quads=False)
                for span in spans:
                    if isinstance(span, pymupdf.Rect):
                        redact_annot = page.add_redact_annot(span)
                        redact_annot.update()
                        count += 1
                page.apply_redactions()
            if replacement:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page.insert_text(
                        (50, 50), replacement,
                        fontsize=12, color=(0, 0, 0)
                    )
            self.editor.canvas_manager.update_preview()
            self.editor.status.configure(text=f"Đã thay thế {count} kết quả")
            return count
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi thay thế: {str(e)}")
            return 0

    def get_page_text(self, page_num):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return ""
            page = doc[page_num]
            return page.get_text("text").strip()
        except Exception as e:
            return ""
