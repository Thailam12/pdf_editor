import pymupdf
from tkinter import messagebox


class SecurityService:
    def __init__(self, editor):
        self.editor = editor

    def set_password(self, user_password, owner_password, page_permissions=None):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            self.editor.undo_manager.save_state(self.editor.elements)
            perms = pymupdf.PERM_ACCESSIBILITY | pymupdf.PERM_PRINT | pymupdf.PERM_COPY
            if page_permissions is not None:
                perms = page_permissions
            doc.encrypt(
                user_password=user_password or "",
                owner_password=owner_password or user_password or "",
                permissions=perms,
            )
            self.editor.status.configure(text="Đã đặt mật khẩu cho PDF")
            messagebox.showinfo("Thành công", "Đã mã hóa PDF với mật khẩu")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đặt mật khẩu: {str(e)}")

    def remove_password(self, password):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            if not doc.is_encrypted:
                messagebox.showinfo("Thông báo", "PDF không được mã hóa")
                return
            if doc.authenticate(password) != 0:
                new_doc = pymupdf.open()
                try:
                    new_doc.insert_pdf(doc)
                finally:
                    doc.close()
                self.editor.pdf_utils.doc = new_doc
                self.editor.canvas_manager.update_preview()
                self.editor.status.configure(text="Đã xóa mật khẩu PDF")
                messagebox.showinfo("Thành công", "Đã giải mã PDF")
            else:
                messagebox.showerror("Lỗi", "Sai mật khẩu!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xóa mật khẩu: {str(e)}")

    def is_encrypted(self):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return False
            return doc.is_encrypted
        except Exception:
            return False

    def check_password(self, password):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return False
            if not doc.is_encrypted:
                return True
            return doc.authenticate(password) != 0
        except Exception:
            return False
