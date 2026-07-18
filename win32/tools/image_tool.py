# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import filedialog, messagebox

def add_image_tool(editor):
    if not editor.current_pdf:
        messagebox.showwarning("Cảnh báo", "Vui lòng mở PDF trước!")
        return
    
    img_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
    if not img_path:
        return
    
    dialog = tk.Toplevel(editor.root)
    dialog.title("Chèn Ảnh")
    dialog.geometry("300x250")
    
    tk.Label(dialog, text="Vị trí X (inch):").pack(pady=5)
    x_var = tk.DoubleVar(value=2.0)
    tk.Entry(dialog, textvariable=x_var, width=20).pack()
    
    tk.Label(dialog, text="Vị trí Y (inch):").pack(pady=5)
    y_var = tk.DoubleVar(value=5.0)
    tk.Entry(dialog, textvariable=y_var, width=20).pack()
    
    tk.Label(dialog, text="Chiều rộng (inch):").pack(pady=5)
    w_var = tk.DoubleVar(value=2.0)
    tk.Entry(dialog, textvariable=w_var, width=20).pack()
    
    tk.Label(dialog, text="Chiều cao (inch):").pack(pady=5)
    h_var = tk.DoubleVar(value=1.5)
    tk.Entry(dialog, textvariable=h_var, width=20).pack()
    
    def apply():
        try:
            editor.undo_manager.save_state(editor.elements)
            from models import ImageElement
            editor.elements.append(ImageElement(
                path=img_path,
                x=x_var.get() * 72,
                y=y_var.get() * 72,
                w=w_var.get() * 72,
                h=h_var.get() * 72,
                page=editor.current_page
            ))
            editor.canvas_manager.update_preview()
            editor.update_info_panel()
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể thêm ảnh: {str(e)}")
    
    tk.Button(dialog, text="Áp dụng", command=apply, bg="#28a745", fg="white", width=15).pack(pady=15)