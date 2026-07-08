# -*- coding: utf-8 -*-
# gui_components.py
import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except Exception:
    ctk = None


def _create_frame(parent, **kwargs):
    if ctk is not None:
        return ctk.CTkFrame(parent, **kwargs)
    return ttk.Frame(parent, **kwargs)


def _create_button(parent, **kwargs):
    if ctk is not None:
        return ctk.CTkButton(parent, **kwargs)
    return ttk.Button(parent, **kwargs)


def _create_label(parent, **kwargs):
    if ctk is not None:
        return ctk.CTkLabel(parent, **kwargs)
    return tk.Label(parent, **kwargs)


def _create_label_frame(parent, text, **kwargs):
    if ctk is not None:
        frame = ctk.CTkFrame(parent, **kwargs)
        label = ctk.CTkLabel(frame, text=text, anchor="w")
        label.pack(anchor="w", padx=10, pady=(10, 6))
        return frame
    return ttk.LabelFrame(parent, text=text, **kwargs)


def create_toolbar(editor, parent=None):
    """Create a more Word-like top toolbar."""
    toolbar_parent = parent or editor.root
    toolbar = _create_frame(toolbar_parent)
    toolbar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4, 2))
    
    # File operations
    _create_button(toolbar, text="📄 Mở PDF", command=editor.open_pdf).pack(side=tk.LEFT, padx=3)
    _create_button(toolbar, text="💾 Lưu PDF", command=editor.save_pdf).pack(side=tk.LEFT, padx=3)
    _create_button(toolbar, text="🖨️ In PDF", command=editor.print_pdf).pack(side=tk.LEFT, padx=3)
    
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
    
    # Edit operations
    _create_button(toolbar, text="↶ Hoàn tác", command=editor.undo).pack(side=tk.LEFT, padx=3)
    _create_button(toolbar, text="↷ Làm lại", command=editor.redo).pack(side=tk.LEFT, padx=3)
    
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
    
    # Text insertion
    _create_button(toolbar, text="🔠 Chèn Chữ", command=editor.add_text).pack(side=tk.LEFT, padx=3)
    _create_button(toolbar, text="🖼️ Chèn Ảnh", command=editor.add_image).pack(side=tk.LEFT, padx=3)
    
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
    
    # Drawing tools
    _create_button(toolbar, text="─ Đường", command=lambda: editor.start_drawing("line")).pack(side=tk.LEFT, padx=3)
    _create_button(toolbar, text="□ Chữ nhật", command=lambda: editor.start_drawing("rect")).pack(side=tk.LEFT, padx=3)
    _create_button(toolbar, text="○ Ellipse", command=lambda: editor.start_drawing("ellipse")).pack(side=tk.LEFT, padx=3)
    _create_button(toolbar, text="△ Tam giác", command=lambda: editor.start_drawing("triangle")).pack(side=tk.LEFT, padx=3)
    _create_button(toolbar, text="🧭 Chọn phần tử", command=editor.toggle_selection_mode).pack(side=tk.LEFT, padx=3)
    
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
    
    # Page navigation
    _create_button(toolbar, text="◀ Trang trước", command=editor.previous_page).pack(side=tk.LEFT, padx=3)
    _create_button(toolbar, text="Trang sau ▶", command=editor.next_page).pack(side=tk.LEFT, padx=3)
    
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
    
    # Clear
    _create_button(toolbar, text="🗑️ Xóa tất cả", command=editor.clear_elements).pack(side=tk.LEFT, padx=3)

def create_formatting_toolbar(editor, parent=None):
    """Create a more Word-like formatting toolbar."""
    toolbar_parent = parent or editor.root
    toolbar = _create_frame(toolbar_parent)
    toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=5)
    
    # Font selection
    _create_label(toolbar, text="Font:").pack(side=tk.LEFT, padx=3)
    font_var = tk.StringVar(value="Arial")
    font_combo = ttk.Combobox(toolbar, textvariable=font_var, 
                              values=["Arial", "Times New Roman", "Courier", "Calibri"], 
                              width=15, state="readonly")
    font_combo.pack(side=tk.LEFT, padx=3)
    font_combo.bind("<<ComboboxSelected>>", lambda e: editor.set_font(font_var.get()))
    editor.font_var = font_var
    
    # Font size
    _create_label(toolbar, text="Kích thước:").pack(side=tk.LEFT, padx=3)
    size_var = tk.IntVar(value=12)
    size_combo = ttk.Combobox(toolbar, textvariable=size_var, 
                              values=[8, 10, 12, 14, 16, 18, 20, 24, 28, 32], 
                              width=8, state="readonly")
    size_combo.pack(side=tk.LEFT, padx=3)
    size_combo.bind("<<ComboboxSelected>>", lambda e: editor.set_font_size(size_var.get()))
    editor.size_var = size_var
    
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
    
    # Text styles
    bold_btn = _create_button(toolbar, text="B", command=editor.toggle_bold, width=3)
    bold_btn.pack(side=tk.LEFT, padx=2)
    editor.bold_btn = bold_btn
    
    italic_btn = _create_button(toolbar, text="I", command=editor.toggle_italic, width=3)
    italic_btn.pack(side=tk.LEFT, padx=2)
    editor.italic_btn = italic_btn
    
    underline_btn = _create_button(toolbar, text="U", command=editor.toggle_underline, width=3)
    underline_btn.pack(side=tk.LEFT, padx=2)
    editor.underline_btn = underline_btn
    
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
    
    # Alignment
    _create_label(toolbar, text="Căn lề:").pack(side=tk.LEFT, padx=3)
    _create_button(toolbar, text="◀", command=lambda: editor.set_alignment("left"), width=3).pack(side=tk.LEFT, padx=2)
    _create_button(toolbar, text="◆", command=lambda: editor.set_alignment("center"), width=3).pack(side=tk.LEFT, padx=2)
    _create_button(toolbar, text="▶", command=lambda: editor.set_alignment("right"), width=3).pack(side=tk.LEFT, padx=2)
    
    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
    
    # Color picker
    _create_button(toolbar, text="🎨 Màu", command=editor.pick_color).pack(side=tk.LEFT, padx=3)

def create_property_panel(editor, parent=None):
    """Create a Word-like right-side properties panel."""
    panel_parent = parent or editor.root
    panel_frame = _create_label_frame(panel_parent, text="Thuộc tính", width=260)
    panel_frame.pack_propagate(False)
    
    # Zoom level
    _create_label(panel_frame, text="Zoom:").pack(anchor="w", padx=10, pady=(10, 5))
    zoom_var = tk.IntVar(value=100)
    zoom_scale = ttk.Scale(panel_frame, from_=50, to=200, orient=tk.HORIZONTAL, 
                           variable=zoom_var, command=lambda v: editor.set_zoom(int(float(v))))
    zoom_scale.pack(fill=tk.X, padx=10, pady=5)
    zoom_label = _create_label(panel_frame, text="100%")
    zoom_label.pack(anchor="w", padx=10)
    editor.zoom_label = zoom_label
    
    # Page info
    ttk.Separator(panel_frame).pack(fill=tk.X, pady=10)
    _create_label(panel_frame, text="Trang:").pack(anchor="w", padx=10)
    editor.page_info = _create_label(panel_frame, text="Trang 1 / 1")
    editor.page_info.pack(anchor="w", padx=10, pady=5)
    
    # Selected element properties
    ttk.Separator(panel_frame).pack(fill=tk.X, pady=10)
    _create_label(panel_frame, text="Phần tử đã chọn:").pack(anchor="w", padx=10)
    editor.selected_title = _create_label(panel_frame, text="Không có phần tử nào", wraplength=180, justify="left")
    editor.selected_title.pack(anchor="w", padx=10, pady=5)
    editor.selected_props_frame = ttk.Frame(panel_frame)
    editor.selected_props_frame.pack(fill=tk.X, padx=10, pady=5)
    _create_button(panel_frame, text="Sửa phần tử", command=editor.edit_selected_element).pack(fill=tk.X, padx=10, pady=(2,4))
    _create_button(panel_frame, text="Xóa phần tử", command=editor.delete_selected_element).pack(fill=tk.X, padx=10, pady=(0,10))
    
    # Element count
    ttk.Separator(panel_frame).pack(fill=tk.X, pady=10)
    _create_label(panel_frame, text="Phần tử:").pack(anchor="w", padx=10)
    editor.element_info = _create_label(panel_frame, text="0 phần tử")
    editor.element_info.pack(anchor="w", padx=10, pady=5)
    
    # Statistics
    ttk.Separator(panel_frame).pack(fill=tk.X, pady=10)
    _create_label(panel_frame, text="Thống kê:").pack(anchor="w", padx=10)
    editor.stats_info = _create_label(panel_frame, text="Chữ: 0\nHình: 0\nĐường: 0")
    editor.stats_info.pack(anchor="w", padx=10, pady=5)
    return panel_frame