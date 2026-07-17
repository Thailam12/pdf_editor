from tkinter import messagebox


class BookmarkService:
    def __init__(self, editor):
        self.editor = editor

    def add_bookmark(self, title, page, parent=None):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            toc = doc.get_toc()
            toc.append([1, title, page + 1])
            doc.set_toc(toc)
            self.editor.canvas_manager.update_preview()
            self.editor.status.configure(text=f"Đã thêm bookmark '{title}' tại trang {page + 1}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm bookmark: {str(e)}")

    def remove_bookmark(self, index):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            toc = doc.get_toc()
            if not toc or index < 0 or index >= len(toc):
                return
            toc.pop(index)
            doc.set_toc(toc)
            self.editor.canvas_manager.update_preview()
            self.editor.status.configure(text="Đã xóa bookmark")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa bookmark: {str(e)}")

    def get_bookmarks(self):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return []
            return doc.get_toc()
        except Exception:
            return []

    def goto_bookmark(self, page):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            target_page = max(0, min(page, len(doc) - 1))
            self.editor.current_page = target_page
            self.editor.selected_element = None
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã đến trang {target_page + 1}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đến bookmark: {str(e)}")

    def reorder_bookmarks(self, from_i, to_i):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            toc = doc.get_toc()
            if not toc or from_i < 0 or from_i >= len(toc) or to_i < 0 or to_i >= len(toc):
                return
            item = toc.pop(from_i)
            toc.insert(to_i, item)
            doc.set_toc(toc)
            self.editor.canvas_manager.update_preview()
            self.editor.status.configure(text="Đã sắp xếp lại bookmark")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể sắp xếp bookmark: {str(e)}")
