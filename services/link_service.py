import webbrowser
from tkinter import messagebox
from models.elements import LinkElement


class LinkService:
    def __init__(self, editor):
        self.editor = editor

    def add_link(self, x, y, w, h, url, text=""):
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            elem = LinkElement(
                x=x, y=y, w=w, h=h,
                url=url, text=text or url,
                page=self.editor.current_page
            )
            self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã thêm liên kết: {url}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm liên kết: {str(e)}")

    def add_page_link(self, x, y, w, h, target_page):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            target_page = max(0, min(target_page, len(doc) - 1))
            self.editor.undo_manager.save_state(self.editor.elements)
            elem = LinkElement(
                x=x, y=y, w=w, h=h,
                url=f"#page={target_page + 1}",
                text=f"Đến trang {target_page + 1}",
                page=self.editor.current_page
            )
            self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã thêm liên kết đến trang {target_page + 1}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm liên kết trang: {str(e)}")

    def open_link(self, element):
        try:
            url = getattr(element, 'url', '')
            if not url:
                return
            if url.startswith('#page='):
                page_num = int(url.split('=')[1]) - 1
                self.editor.current_page = max(0, min(page_num, self.editor.total_pages - 1))
                self.editor.selected_element = None
                self.editor.canvas_manager.update_preview()
                self.editor.update_info_panel()
                self.editor.status.configure(text=f"Đã đến trang {self.editor.current_page + 1}")
            else:
                webbrowser.open_new_tab(url)
                self.editor.status.configure(text=f"Đã mở: {url}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở liên kết: {str(e)}")

    def edit_link(self, element, url):
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            element.url = url
            if not element.text or element.text.startswith("Đến trang") or element.text.startswith("http"):
                element.text = url
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã cập nhật liên kết: {url}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể sửa liên kết: {str(e)}")
