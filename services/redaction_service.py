import pymupdf
from tkinter import messagebox
from models.elements import RedactElement


class RedactionService:
    def __init__(self, editor):
        self.editor = editor

    def mark_for_redaction(self, x, y, w, h):
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            elem = RedactElement(
                x=x, y=y, w=w, h=h,
                color="#000000", label="",
                page=self.editor.current_page
            )
            self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã đánh dấu xóa vùng ({x:.0f}, {y:.0f}, {w:.0f}x{h:.0f})")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đánh dấu xóa: {str(e)}")

    def apply_redactions(self):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            redact_elems = [
                e for e in self.editor.elements
                if getattr(e, 'type_name', '') == 'redact'
            ]
            if not redact_elems:
                messagebox.showinfo("Thông báo", "Không có vùng xóa nào được đánh dấu")
                return
            if not messagebox.askyesno("Xác nhận", "Áp dụng xóa vĩnh viễn? Hành động này không thể hoàn tác!"):
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            for elem in redact_elems:
                page_num = elem.page
                if page_num < 0 or page_num >= len(doc):
                    continue
                page = doc[page_num]
                rect = pymupdf.Rect(elem.x, elem.y, elem.x + elem.w, elem.y + elem.h)
                annot = page.add_redact_annot(rect, fill=None)
                if annot:
                    annot.update()
            for page in doc:
                page.apply_redactions()
            self.editor.elements = [
                e for e in self.editor.elements
                if getattr(e, 'type_name', '') != 'redact'
            ]
            self.editor.element_images.clear()
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã xóa vĩnh viễn {len(redact_elems)} vùng")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể áp dụng xóa: {str(e)}")

    def clear_redactions(self):
        try:
            redact_elems = [
                e for e in self.editor.elements
                if getattr(e, 'type_name', '') == 'redact'
            ]
            if not redact_elems:
                return
            if not messagebox.askyesno("Xác nhận", "Xóa tất cả đánh dấu xóa?"):
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            self.editor.elements = [
                e for e in self.editor.elements
                if getattr(e, 'type_name', '') != 'redact'
            ]
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text="Đã xóa các đánh dấu xóa")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa đánh dấu: {str(e)}")
