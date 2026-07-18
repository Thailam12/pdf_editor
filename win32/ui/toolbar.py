import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except Exception:
    ctk = None


def _frame(parent, **kw):
    return ctk.CTkFrame(parent, **kw) if ctk is not None else ttk.Frame(parent, **kw)


def _btn(parent, **kw):
    return ctk.CTkButton(parent, **kw) if ctk is not None else ttk.Button(parent, **kw)


def create_toolbar(editor, parent=None):
    tb = parent or editor.root
    toolbar = _frame(tb)
    toolbar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4, 2))

    _btn(toolbar, text="📄 Mở PDF", command=editor.open_pdf).pack(side=tk.LEFT, padx=3)
    _btn(toolbar, text="💾 Lưu PDF", command=editor.save_pdf).pack(side=tk.LEFT, padx=3)
    _btn(toolbar, text="🖨️ In PDF", command=editor.print_pdf).pack(side=tk.LEFT, padx=3)
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

    _btn(toolbar, text="↶ Hoàn tác", command=editor.undo).pack(side=tk.LEFT, padx=3)
    _btn(toolbar, text="↷ Làm lại", command=editor.redo).pack(side=tk.LEFT, padx=3)
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

    _btn(toolbar, text="🔠 Chèn Chữ", command=editor.add_text).pack(side=tk.LEFT, padx=3)
    _btn(toolbar, text="🖼️ Chèn Ảnh", command=editor.add_image).pack(side=tk.LEFT, padx=3)
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

    _btn(toolbar, text="─ Đường", command=lambda: editor.start_drawing("line")).pack(side=tk.LEFT, padx=3)
    _btn(toolbar, text="□ Chữ nhật", command=lambda: editor.start_drawing("rect")).pack(side=tk.LEFT, padx=3)
    _btn(toolbar, text="○ Ellipse", command=lambda: editor.start_drawing("ellipse")).pack(side=tk.LEFT, padx=3)
    _btn(toolbar, text="△ Tam giác", command=lambda: editor.start_drawing("triangle")).pack(side=tk.LEFT, padx=3)
    _btn(toolbar, text="🧭 Chọn", command=editor.toggle_selection_mode).pack(side=tk.LEFT, padx=3)

    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
    _btn(toolbar, text="◀ Trang trước", command=editor.previous_page).pack(side=tk.LEFT, padx=3)
    _btn(toolbar, text="Trang sau ▶", command=editor.next_page).pack(side=tk.LEFT, padx=3)
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

    _btn(toolbar, text="🗑️ Xóa tất cả", command=editor.clear_elements).pack(side=tk.LEFT, padx=3)
