import tkinter as tk
from tkinter import ttk, colorchooser

try:
    import customtkinter as ctk
except Exception:
    ctk = None


def _label_frame(parent, text, **kw):
    if ctk is not None:
        frame = ctk.CTkFrame(parent, **kw)
        lbl = ctk.CTkLabel(frame, text=text, anchor="w")
        lbl.pack(anchor="w", padx=10, pady=(10, 6))
        return frame
    return ttk.LabelFrame(parent, text=text, **kw)


def _label(parent, **kw):
    return ctk.CTkLabel(parent, **kw) if ctk is not None else tk.Label(parent, **kw)


def _btn(parent, **kw):
    return ctk.CTkButton(parent, **kw) if ctk is not None else ttk.Button(parent, **kw)


def create_property_panel(editor, parent=None):
    panel_parent = parent or editor.root
    panel = _label_frame(panel_parent, text="Thuộc tính", width=260)
    panel.pack_propagate(False)

    _label(panel, text="Zoom:").pack(anchor="w", padx=10, pady=(10, 5))
    zoom_var = tk.IntVar(value=100)
    zoom_scale = ttk.Scale(panel, from_=50, to=200, orient=tk.HORIZONTAL,
                           variable=zoom_var,
                           command=lambda v: editor.set_zoom(int(float(v))))
    zoom_scale.pack(fill=tk.X, padx=10, pady=5)
    zoom_label = _label(panel, text="100%")
    zoom_label.pack(anchor="w", padx=10)
    editor.zoom_label = zoom_label

    ttk.Separator(panel).pack(fill=tk.X, pady=10)
    _label(panel, text="Trang:").pack(anchor="w", padx=10)
    editor.page_info = _label(panel, text="Trang 1 / 1")
    editor.page_info.pack(anchor="w", padx=10, pady=5)

    ttk.Separator(panel).pack(fill=tk.X, pady=10)
    _label(panel, text="Phần tử đã chọn:").pack(anchor="w", padx=10)
    editor.selected_title = _label(panel, text="Không có phần tử nào", wraplength=180, justify="left")
    editor.selected_title.pack(anchor="w", padx=10, pady=5)
    editor.selected_props_frame = ttk.Frame(panel)
    editor.selected_props_frame.pack(fill=tk.X, padx=10, pady=5)
    _btn(panel, text="Sửa phần tử", command=editor.edit_selected_element).pack(fill=tk.X, padx=10, pady=(2, 4))
    _btn(panel, text="Xóa phần tử", command=editor.delete_selected_element).pack(fill=tk.X, padx=10, pady=(0, 10))

    ttk.Separator(panel).pack(fill=tk.X, pady=10)
    _label(panel, text="Phần tử:").pack(anchor="w", padx=10)
    editor.element_info = _label(panel, text="0 phần tử")
    editor.element_info.pack(anchor="w", padx=10, pady=5)

    ttk.Separator(panel).pack(fill=tk.X, pady=10)
    _label(panel, text="Thống kê:").pack(anchor="w", padx=10)
    editor.stats_info = _label(panel, text="Chữ: 0\nHình: 0\nĐường: 0")
    editor.stats_info.pack(anchor="w", padx=10, pady=5)
    return panel
