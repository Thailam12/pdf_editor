import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from models import TextElement, ImageElement, ShapeElement, LineElement


def edit_element_dialog(editor):
    if editor.selected_element is None or editor.selected_element >= len(editor.elements):
        return
    elem = editor.elements[editor.selected_element]
    if getattr(elem, "page", 0) != editor.current_page:
        editor.selected_element = None
        return

    editor.undo_manager.save_state(editor.elements)

    dialog = tk.Toplevel(editor.root)
    dialog.transient(editor.root)
    dialog.grab_set()
    dialog.title(f"Sửa {elem.type_name or type(elem).__name__}")
    dialog.geometry("420x500")

    vars_map = {}
    row = [0]

    def add_label(text):
        tk.Label(dialog, text=text, anchor="w").grid(row=row[0], column=0, sticky="w", padx=12, pady=4)
        row[0] += 1
        return row[0] - 1

    def add_entry(var, width=16):
        ret = tk.Entry(dialog, textvariable=var, width=width)
        ret.grid(row=row[0] - 1, column=1, sticky="e", padx=12)
        return ret

    add_label("Loại phần tử:")
    tk.Label(dialog, text=elem.type_name.title() if hasattr(elem, 'type_name') else type(elem).__name__,
             anchor="w").grid(row=row[0] - 1, column=1, sticky="e", padx=12)

    if isinstance(elem, TextElement):
        vars_map["text"] = tk.StringVar(value=elem.text)
        add_label("Nội dung:")
        tk.Entry(dialog, textvariable=vars_map["text"], width=35).grid(row=row[0] - 1, column=1, sticky="e", padx=12)
        vars_map["x"] = tk.DoubleVar(value=elem.x / 72)
        add_label("X (inch):")
        add_entry(vars_map["x"])
        vars_map["y"] = tk.DoubleVar(value=elem.y / 72)
        add_label("Y (inch):")
        add_entry(vars_map["y"])
        vars_map["size"] = tk.IntVar(value=elem.size)
        add_label("Kích thước:")
        add_entry(vars_map["size"])
        vars_map["font_name"] = tk.StringVar(value=elem.font_name)
        add_label("Font:")
        ttk.Combobox(dialog, textvariable=vars_map["font_name"],
                     values=["Arial", "Times New Roman", "Courier", "Calibri"],
                     width=14, state="readonly").grid(row=row[0] - 1, column=1, sticky="e", padx=12)
        vars_map["color"] = tk.StringVar(value=elem.color)
        add_label("Màu:")
        c_btn = tk.Button(dialog, text="Chọn màu", bg=elem.color, fg="white")
        c_btn.grid(row=row[0] - 1, column=1, sticky="e", padx=12)
        c_btn.configure(command=lambda: _pick_fill_color(vars_map["color"], c_btn))
    elif isinstance(elem, ImageElement):
        vars_map["path"] = tk.StringVar(value=elem.path)
        add_label("Đường dẫn:")
        tk.Entry(dialog, textvariable=vars_map["path"], width=35).grid(row=row[0] - 1, column=1, sticky="e", padx=12)
        vars_map["x"] = tk.DoubleVar(value=elem.x / 72)
        add_label("X (inch):")
        add_entry(vars_map["x"])
        vars_map["y"] = tk.DoubleVar(value=elem.y / 72)
        add_label("Y (inch):")
        add_entry(vars_map["y"])
        vars_map["w"] = tk.DoubleVar(value=elem.w / 72)
        add_label("Rộng (inch):")
        add_entry(vars_map["w"])
        vars_map["h"] = tk.DoubleVar(value=elem.h / 72)
        add_label("Cao (inch):")
        add_entry(vars_map["h"])
    elif isinstance(elem, ShapeElement):
        vars_map["x"] = tk.DoubleVar(value=elem.x / 72)
        add_label("X (inch):")
        add_entry(vars_map["x"])
        vars_map["y"] = tk.DoubleVar(value=elem.y / 72)
        add_label("Y (inch):")
        add_entry(vars_map["y"])
        vars_map["w"] = tk.DoubleVar(value=elem.w / 72)
        add_label("Rộng (inch):")
        add_entry(vars_map["w"])
        vars_map["h"] = tk.DoubleVar(value=elem.h / 72)
        add_label("Cao (inch):")
        add_entry(vars_map["h"])
        vars_map["color"] = tk.StringVar(value=elem.color)
        add_label("Màu:")
        c_btn = tk.Button(dialog, text="Chọn màu", bg=elem.color, fg="white")
        c_btn.grid(row=row[0] - 1, column=1, sticky="e", padx=12)
        c_btn.configure(command=lambda: _pick_fill_color(vars_map["color"], c_btn))
    elif isinstance(elem, LineElement):
        vars_map["x1"] = tk.DoubleVar(value=elem.x1 / 72)
        add_label("X1 (inch):")
        add_entry(vars_map["x1"])
        vars_map["y1"] = tk.DoubleVar(value=elem.y1 / 72)
        add_label("Y1 (inch):")
        add_entry(vars_map["y1"])
        vars_map["x2"] = tk.DoubleVar(value=elem.x2 / 72)
        add_label("X2 (inch):")
        add_entry(vars_map["x2"])
        vars_map["y2"] = tk.DoubleVar(value=elem.y2 / 72)
        add_label("Y2 (inch):")
        add_entry(vars_map["y2"])
        vars_map["color"] = tk.StringVar(value=elem.color)
        add_label("Màu:")
        c_btn = tk.Button(dialog, text="Chọn màu", bg=elem.color, fg="white")
        c_btn.grid(row=row[0] - 1, column=1, sticky="e", padx=12)
        c_btn.configure(command=lambda: _pick_fill_color(vars_map["color"], c_btn))

    def apply():
        if isinstance(elem, TextElement):
            elem.text = vars_map["text"].get()
            elem.x = vars_map["x"].get() * 72
            elem.y = vars_map["y"].get() * 72
            elem.size = vars_map["size"].get()
            elem.font_name = vars_map["font_name"].get()
            elem.color = vars_map["color"].get()
        elif isinstance(elem, ImageElement):
            elem.path = vars_map["path"].get()
            elem.x = vars_map["x"].get() * 72
            elem.y = vars_map["y"].get() * 72
            elem.w = vars_map["w"].get() * 72
            elem.h = vars_map["h"].get() * 72
        elif isinstance(elem, ShapeElement):
            elem.x = vars_map["x"].get() * 72
            elem.y = vars_map["y"].get() * 72
            elem.w = vars_map["w"].get() * 72
            elem.h = vars_map["h"].get() * 72
            elem.color = vars_map["color"].get()
        elif isinstance(elem, LineElement):
            elem.x1 = vars_map["x1"].get() * 72
            elem.y1 = vars_map["y1"].get() * 72
            elem.x2 = vars_map["x2"].get() * 72
            elem.y2 = vars_map["y2"].get() * 72
            elem.color = vars_map["color"].get()
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        dialog.destroy()

    tk.Button(dialog, text="Lưu thay đổi", command=apply,
              bg="#007bff", fg="white", width=20).grid(row=row[0], column=0, columnspan=2, pady=20)


def _pick_fill_color(var, btn):
    c = colorchooser.askcolor(initialcolor=var.get())[1]
    if c:
        var.set(c)
        btn.configure(bg=c)


def show_about():
    messagebox.showinfo(
        "Về ứng dụng",
        "Word-like Super PDF Editor v2.0\n\n"
        "Một trình chỉnh sửa PDF mạnh mẽ với giao diện tương tự MS Word\n\n"
        "Tính năng:\n"
        "- Chèn và định dạng chữ\n"
        "- Chèn hình ảnh\n"
        "- Vẽ các hình dạng\n"
        "- Hoàn tác/Làm lại\n"
        "- Phóng to/Thu nhỏ\n"
        "- Xuất PDF"
    )
