# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox

def add_text_tool(editor):
    if not editor.current_pdf:
        messagebox.showwarning("Cảnh báo", "Vui lòng mở PDF trước!")
        return
    
    dialog = tk.Toplevel(editor.root)
    dialog.title("Chèn Chữ")
    dialog.geometry("450x480")
    dialog.resizable(False, False)
    
    # Text content
    tk.Label(dialog, text="Nội dung:", font=("Arial", 10)).pack(anchor="w", padx=15, pady=(15,5))
    text_var = tk.StringVar(value="Nhập văn bản...")
    text_entry = tk.Entry(dialog, textvariable=text_var, width=50, font=("Arial", 11))
    text_entry.pack(padx=15, pady=5)
    
    # Position
    frame_pos = ttk.Frame(dialog)
    frame_pos.pack(pady=10, padx=15, fill=tk.X)
    
    tk.Label(frame_pos, text="X (inch):").grid(row=0, column=0, padx=5, sticky="w")
    x_var = tk.DoubleVar(value=2.0)
    tk.Entry(frame_pos, textvariable=x_var, width=10).grid(row=0, column=1, sticky="w")
    
    tk.Label(frame_pos, text="Y (inch):").grid(row=1, column=0, padx=5, sticky="w")
    y_var = tk.DoubleVar(value=6.0)
    tk.Entry(frame_pos, textvariable=y_var, width=10).grid(row=1, column=1, sticky="w")
    
    # Formatting
    frame_format = ttk.LabelFrame(dialog, text="Định dạng", padding=10)
    frame_format.pack(pady=10, padx=15, fill=tk.X)
    
    # Font
    style = editor.formatting_manager.current_style
    tk.Label(frame_format, text="Font:").grid(row=0, column=0, padx=5, sticky="w")
    font_var = tk.StringVar(value=style.font_name)
    font_combo = ttk.Combobox(frame_format, textvariable=font_var,
                              values=["Arial", "Times New Roman", "Courier", "Calibri"],
                              width=15, state="readonly")
    font_combo.grid(row=0, column=1, sticky="w", padx=5)
    
    # Font size
    tk.Label(frame_format, text="Kích thước:").grid(row=1, column=0, padx=5, sticky="w")
    size_var = tk.IntVar(value=style.font_size)
    size_spin = tk.Spinbox(frame_format, from_=8, to=72, textvariable=size_var, width=10)
    size_spin.grid(row=1, column=1, sticky="w", padx=5)
    
    # Style toggles
    bold_var = tk.BooleanVar(value=style.bold)
    italic_var = tk.BooleanVar(value=style.italic)
    underline_var = tk.BooleanVar(value=style.underline)
    tk.Checkbutton(frame_format, text="Đậm", variable=bold_var).grid(row=2, column=0, padx=5, pady=5, sticky="w")
    tk.Checkbutton(frame_format, text="Nghiêng", variable=italic_var).grid(row=2, column=1, padx=5, pady=5, sticky="w")
    tk.Checkbutton(frame_format, text="Gạch chân", variable=underline_var).grid(row=3, column=0, padx=5, pady=5, sticky="w")
    
    # Alignment
    alignment_var = tk.StringVar(value=style.alignment)
    tk.Label(frame_format, text="Căn lề:").grid(row=3, column=1, padx=5, sticky="w")
    align_frame = ttk.Frame(frame_format)
    align_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=5)
    tk.Radiobutton(align_frame, text="Trái", variable=alignment_var, value="left").pack(side="left", padx=3)
    tk.Radiobutton(align_frame, text="Giữa", variable=alignment_var, value="center").pack(side="left", padx=3)
    tk.Radiobutton(align_frame, text="Phải", variable=alignment_var, value="right").pack(side="left", padx=3)
    
    # Color
    current_color = style.color
    color_btn = tk.Button(dialog, text="🎨 Chọn màu chữ", bg=current_color, fg="white")
    color_btn.pack(pady=8)
    
    def pick_color():
        nonlocal current_color
        c = colorchooser.askcolor()[1]
        if c:
            current_color = c
            color_btn.configure(bg=current_color)
    
    color_btn.configure(command=pick_color)

    # Apply button
    def apply():
        if not text_var.get().strip():
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập nội dung!")
            return

        editor.undo_redo_manager.save_state(editor.elements)
        editor.elements.append(("text", {
            "text": text_var.get(),
            "x": x_var.get() * 72,  # Convert inches to points
            "y": y_var.get() * 72,
            "size": size_var.get(),
            "font_name": font_var.get(),
            "color": current_color,
            "bold": bold_var.get(),
            "italic": italic_var.get(),
            "underline": underline_var.get(),
            "alignment": alignment_var.get(),
            "page": editor.current_page
        }))
        editor.update_preview()
        editor.update_info_panel()
        dialog.destroy()
    
    tk.Button(dialog, text="Áp dụng", command=apply, bg="#28a745", fg="white",
              font=("Arial", 10, "bold"), width=15).pack(pady=15)