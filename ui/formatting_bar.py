import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except Exception:
    ctk = None


def _frame(parent, **kw):
    return ctk.CTkFrame(parent, **kw) if ctk is not None else ttk.Frame(parent, **kw)


def _label(parent, **kw):
    return ctk.CTkLabel(parent, **kw) if ctk is not None else tk.Label(parent, **kw)


def _btn(parent, **kw):
    return ctk.CTkButton(parent, **kw) if ctk is not None else ttk.Button(parent, **kw)


def create_formatting_toolbar(editor, parent=None):
    tb = parent or editor.root
    toolbar = _frame(tb)
    toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=5)

    _label(toolbar, text="Font:").pack(side=tk.LEFT, padx=3)
    font_var = tk.StringVar(value="Arial")
    font_combo = ttk.Combobox(toolbar, textvariable=font_var,
                              values=["Arial", "Times New Roman", "Courier", "Calibri"],
                              width=15, state="readonly")
    font_combo.pack(side=tk.LEFT, padx=3)
    font_combo.bind("<<ComboboxSelected>>", lambda e: editor.set_font(font_var.get()))
    editor.font_var = font_var

    _label(toolbar, text="Kích thước:").pack(side=tk.LEFT, padx=3)
    size_var = tk.IntVar(value=12)
    size_combo = ttk.Combobox(toolbar, textvariable=size_var,
                              values=[8, 10, 12, 14, 16, 18, 20, 24, 28, 32],
                              width=8, state="readonly")
    size_combo.pack(side=tk.LEFT, padx=3)
    size_combo.bind("<<ComboboxSelected>>", lambda e: editor.set_font_size(size_var.get()))
    editor.size_var = size_var

    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

    bold_btn = _btn(toolbar, text="B", command=editor.toggle_bold, width=3)
    bold_btn.pack(side=tk.LEFT, padx=2)
    editor.bold_btn = bold_btn

    italic_btn = _btn(toolbar, text="I", command=editor.toggle_italic, width=3)
    italic_btn.pack(side=tk.LEFT, padx=2)
    editor.italic_btn = italic_btn

    underline_btn = _btn(toolbar, text="U", command=editor.toggle_underline, width=3)
    underline_btn.pack(side=tk.LEFT, padx=2)
    editor.underline_btn = underline_btn

    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

    _label(toolbar, text="Căn lề:").pack(side=tk.LEFT, padx=3)
    _btn(toolbar, text="◀", command=lambda: editor.set_alignment("left"), width=3).pack(side=tk.LEFT, padx=2)
    _btn(toolbar, text="◆", command=lambda: editor.set_alignment("center"), width=3).pack(side=tk.LEFT, padx=2)
    _btn(toolbar, text="▶", command=lambda: editor.set_alignment("right"), width=3).pack(side=tk.LEFT, padx=2)

    ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
    _btn(toolbar, text="🎨 Màu", command=editor.pick_color).pack(side=tk.LEFT, padx=3)
