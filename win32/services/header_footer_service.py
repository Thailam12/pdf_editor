from datetime import datetime
from tkinter import messagebox
from models.elements import HeaderFooterElement


class HeaderFooterService:
    def __init__(self, editor):
        self.editor = editor

    def add_page_numbers(self, position="footer-center", start_num=1, fmt="{page} / {total}"):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            total = len(doc)
            positions = {
                "header-left": (36, 10),
                "header-center": (doc[0].rect.width / 2 - 30, 10),
                "header-right": (doc[0].rect.width - 70, 10),
                "footer-left": (36, doc[0].rect.height - 20),
                "footer-center": (doc[0].rect.width / 2 - 30, doc[0].rect.height - 20),
                "footer-right": (doc[0].rect.width - 70, doc[0].rect.height - 20),
            }
            default_x, default_y = positions.get(position, (doc[0].rect.width / 2 - 30, doc[0].rect.height - 20))
            for i in range(total):
                page_num = start_num + i
                text = fmt.replace("{page}", str(page_num)).replace("{total}", str(total))
                elem = HeaderFooterElement(
                    text=text,
                    x=default_x,
                    y=default_y,
                    size=10,
                    color="#666666",
                    position=position,
                    page=i
                )
                self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã thêm số trang (bắt đầu từ {start_num})")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm số trang: {str(e)}")

    def add_text_header(self, text, position="header-center"):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            total = len(doc)
            positions = {
                "header-left": (36, 10),
                "header-center": (doc[0].rect.width / 2 - len(text) * 3, 10),
                "header-right": (doc[0].rect.width - len(text) * 6 - 20, 10),
                "footer-left": (36, doc[0].rect.height - 20),
                "footer-center": (doc[0].rect.width / 2 - len(text) * 3, doc[0].rect.height - 20),
                "footer-right": (doc[0].rect.width - len(text) * 6 - 20, doc[0].rect.height - 20),
            }
            default_x, default_y = positions.get(position, (36, 10))
            for i in range(total):
                elem = HeaderFooterElement(
                    text=text,
                    x=default_x,
                    y=default_y,
                    size=12,
                    color="#333333",
                    position=position,
                    page=i
                )
                self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã thêm header: {text}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm header: {str(e)}")

    def add_date_stamp(self, position="footer-right"):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            total = len(doc)
            now = datetime.now()
            date_text = now.strftime("%d/%m/%Y %H:%M")
            positions = {
                "header-left": (36, 10),
                "header-center": (doc[0].rect.width / 2 - 50, 10),
                "header-right": (doc[0].rect.width - 120, 10),
                "footer-left": (36, doc[0].rect.height - 20),
                "footer-center": (doc[0].rect.width / 2 - 50, doc[0].rect.height - 20),
                "footer-right": (doc[0].rect.width - 120, doc[0].rect.height - 20),
            }
            default_x, default_y = positions.get(position, (doc[0].rect.width - 120, doc[0].rect.height - 20))
            for i in range(total):
                elem = HeaderFooterElement(
                    text=date_text,
                    x=default_x,
                    y=default_y,
                    size=10,
                    color="#666666",
                    position=position,
                    page=i
                )
                self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã thêm ngày tháng: {date_text}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm ngày tháng: {str(e)}")

    def remove_headers_footers(self):
        try:
            if not messagebox.askyesno("Xác nhận", "Xóa tất cả header và footer?"):
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            self.editor.elements = [
                e for e in self.editor.elements
                if getattr(e, 'type_name', '') != 'headerfooter'
            ]
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text="Đã xóa tất cả header và footer")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa header/footer: {str(e)}")
