import os
import tempfile
import pymupdf
from tkinter import messagebox
from copy import deepcopy


class PageService:
    def __init__(self, editor):
        self.editor = editor

    def add_page(self, page_num):
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            insert_at = min(page_num + 1, len(doc))
            doc.new_page(pno=insert_at, width=doc[0].rect.width, height=doc[0].rect.height)
            self.editor.total_pages = len(doc)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã thêm trang sau trang {page_num + 1}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm trang: {str(e)}")

    def delete_page(self, page_num):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or len(doc) <= 1:
                messagebox.showwarning("Cảnh báo", "Không thể xóa trang cuối cùng!")
                return
            if not messagebox.askyesno("Xác nhận", f"Xóa trang {page_num + 1}?"):
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            self.editor.elements = [e for e in self.editor.elements if getattr(e, 'page', 0) != page_num]
            for e in self.editor.elements:
                ep = getattr(e, 'page', 0)
                if ep > page_num:
                    e.page = ep - 1
            doc.delete_page(page_num)
            self.editor.total_pages = len(doc)
            if self.editor.current_page >= self.editor.total_pages:
                self.editor.current_page = self.editor.total_pages - 1
            self.editor.selected_element = None
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã xóa trang {page_num + 1}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa trang: {str(e)}")

    def move_page(self, from_idx, to_idx):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            if from_idx == to_idx:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            self.editor.current_pdf = None
            doc.move_page(from_idx, to_idx)
            for e in self.editor.elements:
                ep = getattr(e, 'page', 0)
                if ep == from_idx:
                    e.page = to_idx
                elif from_idx < to_idx and ep > from_idx and ep <= to_idx:
                    e.page = ep - 1
                elif from_idx > to_idx and ep >= to_idx and ep < from_idx:
                    e.page = ep + 1
            if self.editor.current_page == from_idx:
                self.editor.current_page = to_idx
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã di chuyển trang {from_idx + 1} đến {to_idx + 1}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể di chuyển trang: {str(e)}")

    def rotate_page(self, page_num, angle):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            page = doc[page_num]
            current = page.rotation or 0
            page.set_rotation((current + angle) % 360)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã xoay trang {page_num + 1} {angle} độ")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xoay trang: {str(e)}")

    def crop_page(self, page_num, x, y, w, h):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            page = doc[page_num]
            rect = pymupdf.Rect(x, y, x + w, y + h)
            page.set_cropbox(rect)
            self.editor.canvas_manager.update_preview()
            self.editor.status.configure(text=f"Đã cắt trang {page_num + 1}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể cắt trang: {str(e)}")

    def merge_pdfs(self, paths):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            if not paths:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            current_page_count = len(doc)
            for pdf_path in paths:
                if not os.path.exists(pdf_path):
                    continue
                src_doc = pymupdf.open(pdf_path)
                try:
                    doc.insert_pdf(src_doc)
                finally:
                    src_doc.close()
            self.editor.total_pages = len(doc)
            self.editor.current_pdf = None
            self.editor.is_temp_document = True
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã ghép {len(paths)} file PDF")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể ghép PDF: {str(e)}")

    def split_pdf(self, ranges):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            if not ranges:
                messagebox.showwarning("Cảnh báo", "Vui lòng chỉ định phạm vi trang!")
                return
            import tkinter.filedialog as fd
            out_dir = fd.askdirectory(title="Chọn thư mục lưu các file PDF đã tách")
            if not out_dir:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            for i, (start, end) in enumerate(ranges):
                start = max(0, min(start, len(doc) - 1))
                end = max(start, min(end, len(doc) - 1))
                new_doc = pymupdf.open()
                try:
                    new_doc.insert_pdf(doc, from_page=start, to_page=end)
                    out_path = os.path.join(out_dir, f"split_{i + 1}_pages_{start + 1}_{end + 1}.pdf")
                    new_doc.save(out_path)
                finally:
                    new_doc.close()
            self.editor.status.configure(text=f"Đã tách PDF thành {len(ranges)} file")
            messagebox.showinfo("Thành công", f"Đã tách thành {len(ranges)} file PDF vào thư mục đã chọn")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tách PDF: {str(e)}")

    def duplicate_page(self, page_num):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            new_doc = pymupdf.open()
            try:
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                doc.insert_pdf(new_doc, from_page=0, to_page=0, start_at=page_num + 1)
            finally:
                new_doc.close()
            dup_elements = []
            for e in self.editor.elements:
                ep = getattr(e, 'page', 0)
                if ep == page_num:
                    new_e = deepcopy(e)
                    new_e.page = page_num + 1
                    dup_elements.append(new_e)
                elif ep > page_num:
                    e.page = ep + 1
            self.editor.elements.extend(dup_elements)
            self.editor.total_pages = len(doc)
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã nhân đôi trang {page_num + 1}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể nhân đôi trang: {str(e)}")

    def resize_page(self, page_num, w, h):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            page = doc[page_num]
            rect = pymupdf.Rect(0, 0, w, h)
            page.set_mediabox(rect)
            self.editor.canvas_manager.update_preview()
            self.editor.status.configure(text=f"Đã thay đổi kích thước trang {page_num + 1}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thay đổi kích thước trang: {str(e)}")
