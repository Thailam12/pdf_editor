import os
import pymupdf
from tkinter import messagebox
from models.elements import WatermarkElement


class WatermarkService:
    def __init__(self, editor):
        self.editor = editor

    def add_text_watermark(self, text, page, size=60, color="#888888", opacity=0.3, rotation=45):
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            pages_to_apply = []
            if page == -1:
                pages_to_apply = list(range(len(doc)))
            else:
                pages_to_apply = [page]
            for pno in pages_to_apply:
                pdf_page = doc[pno]
                rect = pdf_page.rect
                cx = rect.width / 2
                cy = rect.height / 2
                elem = WatermarkElement(
                    text=text, x=cx, y=cy, size=size,
                    color=color, opacity=opacity, rotation=rotation,
                    page=pno
                )
                self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            page_label = "tất cả các trang" if page == -1 else f"trang {page + 1}"
            self.editor.status.configure(text=f"Đã thêm watermark '{text}' vào {page_label}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm watermark: {str(e)}")

    def add_image_watermark(self, path, page, opacity=0.3, scale=1.0):
        try:
            if not os.path.exists(path):
                messagebox.showerror("Lỗi", "Không tìm thấy file ảnh!")
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            from PIL import Image
            img = Image.open(path)
            img_w, img_h = img.size
            pages_to_apply = []
            if page == -1:
                pages_to_apply = list(range(len(doc)))
            else:
                pages_to_apply = [page]
            from models.elements import ImageElement
            for pno in pages_to_apply:
                pdf_page = doc[pno]
                rect = pdf_page.rect
                cx = rect.width / 2 - (img_w * scale) / 2
                cy = rect.height / 2 - (img_h * scale) / 2
                elem = ImageElement(
                    path=path, x=cx, y=cy,
                    w=img_w * scale, h=img_h * scale,
                    page=pno
                )
                elem.opacity = opacity
                self.editor.elements.append(elem)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            page_label = "tất cả các trang" if page == -1 else f"trang {page + 1}"
            self.editor.status.configure(text=f"Đã thêm watermark ảnh vào {page_label}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm watermark ảnh: {str(e)}")

    def remove_watermarks(self):
        try:
            if not messagebox.askyesno("Xác nhận", "Xóa tất cả watermark?"):
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            self.editor.elements = [
                e for e in self.editor.elements
                if getattr(e, 'type_name', '') != 'watermark'
            ]
            self.editor.element_images.clear()
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text="Đã xóa tất cả watermark")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa watermark: {str(e)}")

    def preview_watermark(self, text, size=60, color="#888888", opacity=0.3, rotation=45):
        try:
            self.editor.canvas_manager.update_preview()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xem trước watermark: {str(e)}")
