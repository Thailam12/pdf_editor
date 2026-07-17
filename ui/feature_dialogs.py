import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
import os

try:
    import customtkinter as ctk
except Exception:
    ctk = None

from models.elements import (
    PREDEFINED_STAMPS, StampElement, SignatureElement, WatermarkElement,
    FormFieldElement, HeaderFooterElement,
)

BG = "#1e1e2e"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
BTN_BG = "#45475a"
ENTRY_BG = "#313244"
ACTIVE_BG = "#585b70"


class _DialogBase:
    def __init__(self, editor, title, geometry="450x500"):
        self.editor = editor
        self.result = None
        self.dialog = tk.Toplevel(editor.root)
        self.dialog.transient(editor.root)
        self.dialog.grab_set()
        self.dialog.title(title)
        self.dialog.geometry(geometry)
        self.dialog.configure(bg=BG)
        self.dialog.protocol("WM_DELETE_WINDOW", self._cancel)

        self.main_frame = tk.Frame(self.dialog, bg=BG)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.content_frame = tk.Frame(self.main_frame, bg=BG)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.button_frame = tk.Frame(self.main_frame, bg=BG)
        self.button_frame.pack(fill=tk.X, pady=(12, 0))

        ok_btn = tk.Button(self.button_frame, text="OK", command=self._ok,
                           bg=ACCENT, fg=BG, font=("Segoe UI", 9, "bold"),
                           relief="flat", bd=0, padx=20, pady=4, cursor="hand2")
        ok_btn.pack(side=tk.RIGHT, padx=(8, 0))

        cancel_btn = tk.Button(self.button_frame, text="Cancel", command=self._cancel,
                               bg=BTN_BG, fg=FG, font=("Segoe UI", 9),
                               relief="flat", bd=0, padx=20, pady=4, cursor="hand2")
        cancel_btn.pack(side=tk.RIGHT)

    def _ok(self):
        self.result = self._get_result()
        self.dialog.destroy()

    def _cancel(self):
        self.result = None
        self.dialog.destroy()

    def _get_result(self):
        return None

    def show(self):
        self.dialog.wait_window()
        return self.result

    def _add_label(self, parent, text, **kw):
        lbl = tk.Label(parent, text=text, bg=BG, fg=FG,
                       font=("Segoe UI", 9), anchor="w", **kw)
        return lbl

    def _add_entry(self, parent, variable, width=25):
        entry = tk.Entry(parent, textvariable=variable, width=width,
                         bg=ENTRY_BG, fg=FG, insertbackground=FG,
                         font=("Segoe UI", 9), relief="flat", bd=4)
        return entry

    def _add_combobox(self, parent, variable, values, width=15):
        combo = ttk.Combobox(parent, textvariable=variable, values=values,
                             width=width, state="readonly")
        return combo

    def _add_checkbutton(self, parent, text, variable):
        cb = tk.Checkbutton(parent, text=text, variable=variable,
                            bg=BG, fg=FG, selectcolor=BTN_BG,
                            activebackground=BG, activeforeground=FG,
                            font=("Segoe UI", 9))
        return cb


def stamp_dialog(editor):
    d = _DialogBase(editor, "Insert Stamp", "500x550")

    tk.Label(d.content_frame, text="Predefined Stamps", bg=BG, fg=FG,
             font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))

    grid_frame = tk.Frame(d.content_frame, bg=BG)
    grid_frame.pack(fill=tk.X, pady=(0, 12))

    selected_stamp = {"value": None}

    for i, stamp in enumerate(PREDEFINED_STAMPS):
        row, col = divmod(i, 4)
        btn = tk.Button(
            grid_frame,
            text=f"{stamp['icon']} {stamp['text']}",
            bg=stamp["color"],
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            bd=0,
            padx=8,
            pady=6,
            cursor="hand2",
            command=lambda s=stamp: _select_stamp(s, selected_stamp, d),
        )
        btn.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
        grid_frame.columnconfigure(col, weight=1)

    ttk.Separator(d.content_frame, orient="horizontal").pack(fill=tk.X, pady=8)

    tk.Label(d.content_frame, text="Custom Stamp", bg=BG, fg=FG,
             font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))

    custom_frame = tk.Frame(d.content_frame, bg=BG)
    custom_frame.pack(fill=tk.X)

    tk.Label(custom_frame, text="Text:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=(0, 8))
    custom_text = tk.StringVar(value="")
    d._add_entry(custom_frame, custom_text, 30).grid(row=0, column=1, sticky="ew")

    tk.Label(custom_frame, text="Color:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
    custom_color = tk.StringVar(value="#CC0000")
    color_btn = tk.Button(custom_frame, text="Choose", bg=custom_color.get(), fg="white",
                          font=("Segoe UI", 8), relief="flat", cursor="hand2",
                          command=lambda: _pick_color(custom_color, color_btn))
    color_btn.grid(row=1, column=1, sticky="w", pady=(8, 0))

    custom_frame.columnconfigure(1, weight=1)

    def _select_stamp(stamp, sel, dialog):
        sel["value"] = stamp

    def _pick_color(var, btn):
        c = colorchooser.askcolor(initialcolor=var.get())[1]
        if c:
            var.set(c)
            btn.configure(bg=c)

    d._pick_color = _pick_color

    def on_ok():
        stamp = selected_stamp.get("value")
        if stamp:
            elem = StampElement(
                text=stamp["text"],
                color=stamp["color"],
                page=editor.current_page,
            )
            editor.undo_manager.save_state(editor.elements)
            editor.elements.append(elem)
            editor.canvas_manager.update_preview()
            editor.update_info_panel()
            d.dialog.destroy()
            return
        custom_t = custom_text.get().strip()
        if custom_t:
            elem = StampElement(
                text=custom_t,
                color=custom_color.get(),
                page=editor.current_page,
            )
            editor.undo_manager.save_state(editor.elements)
            editor.elements.append(elem)
            editor.canvas_manager.update_preview()
            editor.update_info_panel()
            d.dialog.destroy()
            return
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def signature_dialog(editor):
    d = _DialogBase(editor, "Insert Signature", "520x480")

    mode_var = tk.StringVar(value="type")

    mode_frame = tk.Frame(d.content_frame, bg=BG)
    mode_frame.pack(fill=tk.X, pady=(0, 12))

    for mode, label in [("draw", "Draw"), ("type", "Type"), ("upload", "Upload")]:
        rb = tk.Radiobutton(mode_frame, text=label, variable=mode_var, value=mode,
                            bg=BG, fg=FG, selectcolor=BTN_BG,
                            activebackground=BG, activeforeground=FG,
                            font=("Segoe UI", 9),
                            command=lambda m=mode: _switch_mode(m))
        rb.pack(side=tk.LEFT, padx=8)

    draw_frame = tk.Frame(d.content_frame, bg=BG)
    type_frame = tk.Frame(d.content_frame, bg=BG)
    upload_frame = tk.Frame(d.content_frame, bg=BG)

    draw_canvas = tk.Canvas(draw_frame, width=400, height=200,
                            bg="#ffffff", bd=1, relief="solid", cursor="pencil")
    draw_canvas.pack(pady=8)
    draw_points = []

    def on_draw_press(event):
        draw_points.append((event.x, event.y))

    def on_draw_motion(event):
        if draw_points:
            x1, y1 = draw_points[-1]
            draw_canvas.create_line(x1, y1, event.x, event.y,
                                    fill="#000000", width=2, smooth=True)
            draw_points.append((event.x, event.y))

    def clear_draw():
        draw_canvas.delete("all")
        draw_points.clear()

    tk.Button(draw_frame, text="Clear", command=clear_draw,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(pady=4)

    draw_canvas.bind("<ButtonPress-1>", on_draw_press)
    draw_canvas.bind("<B1-Motion>", on_draw_motion)

    tk.Label(type_frame, text="Type your signature:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 8))
    sig_text = tk.StringVar(value="")
    d._add_entry(type_frame, sig_text, 35).pack(anchor="w")

    tk.Label(type_frame, text="Preview:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 4))
    preview_label = tk.Label(type_frame, text="", bg="#ffffff", fg="#000000",
                             font=("Segoe UI", 18), width=30, height=2,
                             relief="solid")
    preview_label.pack(anchor="w", pady=4)

    def update_preview(*args):
        t = sig_text.get()
        preview_label.configure(text=t if t else "Signature")

    sig_text.trace_add("write", update_preview)
    update_preview()

    tk.Label(upload_frame, text="Upload signature image:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 8))
    upload_path = tk.StringVar(value="")

    def browse_file():
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All", "*.*")]
        )
        if path:
            upload_path.set(path)

    path_frame = tk.Frame(upload_frame, bg=BG)
    path_frame.pack(fill=tk.X)
    d._add_entry(path_frame, upload_path, 30).pack(side=tk.LEFT)
    tk.Button(path_frame, text="Browse...", command=browse_file,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(side=tk.LEFT, padx=4)

    color_var = tk.StringVar(value="#000066")

    def _switch_mode(mode):
        draw_frame.pack_forget()
        type_frame.pack_forget()
        upload_frame.pack_forget()
        if mode == "draw":
            draw_frame.pack(fill=tk.X)
        elif mode == "type":
            type_frame.pack(fill=tk.X)
        elif mode == "upload":
            upload_frame.pack(fill=tk.X)

    _switch_mode("type")

    def on_ok():
        mode = mode_var.get()
        text_val = sig_text.get().strip() if mode == "type" else ""
        img_data = ""
        if mode == "upload":
            img_data = upload_path.get()

        elem = SignatureElement(
            text=text_val,
            image_data=img_data,
            color=color_var.get(),
            page=editor.current_page,
        )
        editor.undo_manager.save_state(editor.elements)
        editor.elements.append(elem)
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def watermark_dialog(editor):
    d = _DialogBase(editor, "Add Watermark", "420x420")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X)

    tk.Label(fields, text="Text:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    wm_text = tk.StringVar(value="WATERMARK")
    d._add_entry(fields, wm_text).grid(row=0, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Font Size:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    wm_size = tk.IntVar(value=60)
    d._add_entry(fields, wm_size, 10).grid(row=1, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Rotation:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    wm_rotation = tk.IntVar(value=45)
    d._add_entry(fields, wm_rotation, 10).grid(row=2, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Opacity:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=3, column=0, sticky="w", pady=4, padx=(0, 8))
    wm_opacity = tk.DoubleVar(value=0.3)
    d._add_entry(fields, wm_opacity, 10).grid(row=3, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Color:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=4, column=0, sticky="w", pady=4, padx=(0, 8))
    wm_color = tk.StringVar(value="#888888")

    def pick_wm_color():
        c = colorchooser.askcolor(initialcolor=wm_color.get())[1]
        if c:
            wm_color.set(c)
            color_display.configure(bg=c)

    color_frame = tk.Frame(fields, bg=BG)
    color_frame.grid(row=4, column=1, sticky="w", pady=4)
    color_display = tk.Button(color_frame, text="Choose", bg=wm_color.get(), fg="white",
                              font=("Segoe UI", 8), relief="flat", cursor="hand2",
                              command=pick_wm_color)
    color_display.pack(side=tk.LEFT)

    apply_var = tk.StringVar(value="current")
    apply_frame = tk.Frame(d.content_frame, bg=BG)
    apply_frame.pack(fill=tk.X, pady=(12, 0))
    tk.Label(apply_frame, text="Apply to:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 4))
    tk.Radiobutton(apply_frame, text="Current Page", variable=apply_var, value="current",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(anchor="w")
    tk.Radiobutton(apply_frame, text="All Pages", variable=apply_var, value="all",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(anchor="w")

    fields.columnconfigure(1, weight=1)

    def on_ok():
        text = wm_text.get().strip()
        if not text:
            messagebox.showwarning("Warning", "Watermark text cannot be empty.")
            return
        pages = range(editor.total_pages) if apply_var.get() == "all" else [editor.current_page]
        editor.undo_manager.save_state(editor.elements)
        for pg in pages:
            elem = WatermarkElement(
                text=text,
                size=wm_size.get(),
                rotation=wm_rotation.get(),
                opacity=wm_opacity.get(),
                color=wm_color.get(),
                page=pg,
            )
            editor.elements.append(elem)
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def page_properties_dialog(editor):
    d = _DialogBase(editor, "Page Properties", "400x350")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X)

    sizes = ["Letter (8.5x11)", "A4 (210x297mm)", "Legal (8.5x14)", "A3 (297x420mm)", "Custom"]
    tk.Label(fields, text="Page Size:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    size_var = tk.StringVar(value="A4 (210x297mm)")
    d._add_combobox(fields, size_var, sizes).grid(row=0, column=1, sticky="ew", pady=4)

    orientations = ["Portrait", "Landscape"]
    tk.Label(fields, text="Orientation:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    orient_var = tk.StringVar(value="Portrait")
    d._add_combobox(fields, orient_var, orientations).grid(row=1, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Margins (points):", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    margins_frame = tk.Frame(fields, bg=BG)
    margins_frame.grid(row=2, column=1, sticky="ew", pady=4)

    margin_vars = {}
    for i, label in enumerate(["Top", "Bottom", "Left", "Right"]):
        tk.Label(margins_frame, text=f"{label}:", bg=BG, fg=FG,
                 font=("Segoe UI", 8)).grid(row=0, column=i * 2, padx=2)
        var = tk.IntVar(value=72)
        tk.Entry(margins_frame, textvariable=var, width=5, bg=ENTRY_BG, fg=FG,
                 insertbackground=FG, font=("Segoe UI", 8), relief="flat", bd=3).grid(
            row=0, column=i * 2 + 1, padx=2)
        margin_vars[label.lower()] = var

    fields.columnconfigure(1, weight=1)

    def on_ok():
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def ocr_dialog(editor):
    d = _DialogBase(editor, "OCR Recognition", "500x450")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X, pady=(0, 12))

    tk.Label(fields, text="Language:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    lang_var = tk.StringVar(value="eng")
    d._add_combobox(fields, lang_var,
                    ["eng", "vie", "chi_sim", "jpn", "kor", "fra", "deu", "spa"],
                    width=15).grid(row=0, column=1, sticky="w", pady=4)

    range_frame = tk.Frame(d.content_frame, bg=BG)
    range_frame.pack(fill=tk.X, pady=(0, 12))

    range_var = tk.StringVar(value="current")
    tk.Radiobutton(range_frame, text="Current Page", variable=range_var, value="current",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(anchor="w")
    tk.Radiobutton(range_frame, text="All Pages", variable=range_var, value="all",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(anchor="w")

    custom_frame = tk.Frame(range_frame, bg=BG)
    custom_frame.pack(anchor="w")
    tk.Radiobutton(custom_frame, text="Range:", variable=range_var, value="range",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(side=tk.LEFT)
    range_start = tk.IntVar(value=1)
    range_end = tk.IntVar(value=editor.total_pages if editor.total_pages > 0 else 1)
    tk.Entry(custom_frame, textvariable=range_start, width=5, bg=ENTRY_BG, fg=FG,
             insertbackground=FG, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)
    tk.Label(custom_frame, text="to", bg=BG, fg=FG, font=("Segoe UI", 9)).pack(side=tk.LEFT)
    tk.Entry(custom_frame, textvariable=range_end, width=5, bg=ENTRY_BG, fg=FG,
             insertbackground=FG, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=4)

    progress_frame = tk.Frame(d.content_frame, bg=BG)
    progress_frame.pack(fill=tk.X, pady=(0, 12))
    progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=400)
    progress_bar.pack(fill=tk.X)
    status_label = tk.Label(progress_frame, text="Ready", bg=BG, fg="#a6adc8",
                            font=("Segoe UI", 8))
    status_label.pack(anchor="w", pady=(4, 0))

    results_frame = tk.Frame(d.content_frame, bg=BG)
    results_frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(results_frame, text="Results:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

    results_text = tk.Text(results_frame, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                           font=("Consolas", 9), relief="flat", bd=4, height=8,
                           wrap=tk.WORD)
    results_scroll = ttk.Scrollbar(results_frame, command=results_text.yview)
    results_text.configure(yscrollcommand=results_scroll.set)
    results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    results_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def on_ok():
        if editor.ocr_running:
            messagebox.showinfo("Info", "OCR is already running.")
            return
        status_label.configure(text="Processing...")
        progress_bar["value"] = 20
        d.dialog.update()
        try:
            editor.ocr_current_page_dialog() if range_var.get() == "current" else editor.ocr_all_pages_dialog()
            progress_bar["value"] = 100
            status_label.configure(text="Complete")
        except Exception as ex:
            status_label.configure(text=f"Error: {str(ex)}")
            progress_bar["value"] = 0

    d._ok = on_ok
    return d.show()


def protect_dialog(editor):
    d = _DialogBase(editor, "Password Protect", "400x350")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X)

    tk.Label(fields, text="Password:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    pw_var = tk.StringVar()
    pw_entry = tk.Entry(fields, textvariable=pw_var, show="*", width=25,
                        bg=ENTRY_BG, fg=FG, insertbackground=FG,
                        font=("Segoe UI", 9), relief="flat", bd=4)
    pw_entry.grid(row=0, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Confirm:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    pw2_var = tk.StringVar()
    tk.Entry(fields, textvariable=pw2_var, show="*", width=25,
             bg=ENTRY_BG, fg=FG, insertbackground=FG,
             font=("Segoe UI", 9), relief="flat", bd=4).grid(row=1, column=1, sticky="ew", pady=4)

    fields.columnconfigure(1, weight=1)

    perm_frame = tk.Frame(d.content_frame, bg=BG)
    perm_frame.pack(fill=tk.X, pady=(16, 0))
    tk.Label(perm_frame, text="Permissions:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

    perm_vars = {}
    for label in ["Allow Printing", "Allow Copying", "Allow Editing", "Allow Annotating"]:
        var = tk.BooleanVar(value=True)
        d._add_checkbutton(perm_frame, label, var).pack(anchor="w")
        perm_vars[label] = var

    def on_ok():
        pw = pw_var.get()
        pw2 = pw2_var.get()
        if pw and pw != pw2:
            messagebox.showwarning("Warning", "Passwords do not match.")
            return
        if not pw:
            messagebox.showwarning("Warning", "Please enter a password.")
            return
        messagebox.showinfo("Info", "Password protection applied (simulated).")
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def bookmarks_dialog(editor):
    d = _DialogBase(editor, "Bookmarks", "400x400")

    tree_frame = tk.Frame(d.content_frame, bg=BG)
    tree_frame.pack(fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(tree_frame, columns=("page",), selectmode="browse")
    tree.heading("#0", text="Bookmark")
    tree.heading("page", text="Page")
    tree.column("#0", width=250)
    tree.column("page", width=80, anchor="center")

    tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=tree_scroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    if editor.current_pdf and editor.total_pages > 0:
        for i in range(editor.total_pages):
            tree.insert("", "end", text=f"Page {i + 1}", values=(i + 1,))

    btn_frame = tk.Frame(d.content_frame, bg=BG)
    btn_frame.pack(fill=tk.X, pady=(8, 0))

    def add_bookmark():
        name = tk.simpledialog.askstring("Add Bookmark", "Bookmark name:") if hasattr(tk, 'simpledialog') else "Bookmark"
        if name:
            sel = tree.selection()
            parent = sel[0] if sel else ""
            tree.insert(parent, "end", text=name, values=(editor.current_page + 1,))

    def delete_bookmark():
        sel = tree.selection()
        if sel:
            tree.delete(sel[0])

    tk.Button(btn_frame, text="Add", command=add_bookmark,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=12).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Delete", command=delete_bookmark,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=12).pack(side=tk.LEFT, padx=2)

    return d.show()


def split_dialog(editor):
    d = _DialogBase(editor, "Split PDF", "420x350")

    mode_var = tk.StringVar(value="range")

    modes_frame = tk.Frame(d.content_frame, bg=BG)
    modes_frame.pack(fill=tk.X, pady=(0, 12))

    tk.Radiobutton(modes_frame, text="By Page Range", variable=mode_var, value="range",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(anchor="w")
    tk.Radiobutton(modes_frame, text="Every N Pages", variable=mode_var, value="every_n",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(anchor="w")
    tk.Radiobutton(modes_frame, text="By Bookmarks", variable=mode_var, value="bookmarks",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(anchor="w")

    range_frame = tk.Frame(d.content_frame, bg=BG)
    range_frame.pack(fill=tk.X)

    tk.Label(range_frame, text="Start Page:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    start_var = tk.IntVar(value=1)
    d._add_entry(range_frame, start_var, 10).grid(row=0, column=1, sticky="w", pady=4)

    tk.Label(range_frame, text="End Page:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    end_var = tk.IntVar(value=editor.total_pages if editor.total_pages > 0 else 1)
    d._add_entry(range_frame, end_var, 10).grid(row=1, column=1, sticky="w", pady=4)

    tk.Label(range_frame, text="Pages per split:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    n_var = tk.IntVar(value=5)
    d._add_entry(range_frame, n_var, 10).grid(row=2, column=1, sticky="w", pady=4)

    def on_ok():
        mode = mode_var.get()
        messagebox.showinfo("Split", f"Split operation ({mode}) would execute here.")
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def find_replace_dialog(editor):
    d = _DialogBase(editor, "Find & Replace", "500x420")

    search_frame = tk.Frame(d.content_frame, bg=BG)
    search_frame.pack(fill=tk.X, pady=(0, 8))

    tk.Label(search_frame, text="Find:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    find_var = tk.StringVar()
    d._add_entry(search_frame, find_var, 35).grid(row=0, column=1, sticky="ew", pady=4)

    tk.Label(search_frame, text="Replace:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    replace_var = tk.StringVar()
    d._add_entry(search_frame, replace_var, 35).grid(row=1, column=1, sticky="ew", pady=4)

    search_frame.columnconfigure(1, weight=1)

    opts_frame = tk.Frame(d.content_frame, bg=BG)
    opts_frame.pack(fill=tk.X, pady=(0, 8))
    match_case_var = tk.BooleanVar(value=False)
    whole_word_var = tk.BooleanVar(value=False)
    d._add_checkbutton(opts_frame, "Match Case", match_case_var).pack(side=tk.LEFT, padx=4)
    d._add_checkbutton(opts_frame, "Whole Word", whole_word_var).pack(side=tk.LEFT, padx=4)

    btn_frame = tk.Frame(d.content_frame, bg=BG)
    btn_frame.pack(fill=tk.X, pady=(0, 8))

    results_list = []

    def do_find():
        results_text.delete("1.0", tk.END)
        results_list.clear()
        query = find_var.get()
        if not query:
            return
        for i, elem in enumerate(editor.elements):
            text = getattr(elem, "text", "")
            if text and query.lower() in text.lower():
                results_text.insert(tk.END, f"Page {elem.page + 1}: {text[:50]}...\n")
                results_list.append(i)

    def do_replace():
        if not results_list:
            return
        query = find_var.get()
        replacement = replace_var.get()
        if not query:
            return
        editor.undo_manager.save_state(editor.elements)
        count = 0
        for i in results_list:
            if i < len(editor.elements):
                elem = editor.elements[i]
                if hasattr(elem, "text") and query.lower() in elem.text.lower():
                    if match_case_var.get():
                        elem.text = elem.text.replace(query, replacement)
                    else:
                        import re
                        elem.text = re.sub(re.escape(query), replacement, elem.text, flags=re.IGNORECASE)
                    count += 1
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        do_find()

    tk.Button(btn_frame, text="Find All", command=do_find,
              bg=ACCENT, fg=BG, font=("Segoe UI", 9, "bold"), relief="flat",
              cursor="hand2", padx=12).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Replace", command=do_replace,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 9), relief="flat",
              cursor="hand2", padx=12).pack(side=tk.LEFT, padx=2)

    results_frame = tk.Frame(d.content_frame, bg=BG)
    results_frame.pack(fill=tk.BOTH, expand=True)
    tk.Label(results_frame, text="Results:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

    results_text = tk.Text(results_frame, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                           font=("Consolas", 9), relief="flat", bd=4, height=6,
                           wrap=tk.WORD)
    results_scroll = ttk.Scrollbar(results_frame, command=results_text.yview)
    results_text.configure(yscrollcommand=results_scroll.set)
    results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    results_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    return d.show()


def compare_dialog(editor):
    d = _DialogBase(editor, "Compare PDFs", "450x300")

    tk.Label(d.content_frame, text="File 1:", bg=BG, fg=FG, font=("Segoe UI", 9)).pack(
        anchor="w", pady=(0, 4))
    file1_var = tk.StringVar()
    f1_frame = tk.Frame(d.content_frame, bg=BG)
    f1_frame.pack(fill=tk.X, pady=(0, 8))
    d._add_entry(f1_frame, file1_var, 35).pack(side=tk.LEFT)
    tk.Button(f1_frame, text="Browse...",
              command=lambda: file1_var.set(filedialog.askopenfilename(
                  filetypes=[("PDF", "*.pdf")]) or file1_var.get()),
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(side=tk.LEFT, padx=4)

    tk.Label(d.content_frame, text="File 2:", bg=BG, fg=FG, font=("Segoe UI", 9)).pack(
        anchor="w", pady=(0, 4))
    file2_var = tk.StringVar()
    f2_frame = tk.Frame(d.content_frame, bg=BG)
    f2_frame.pack(fill=tk.X, pady=(0, 8))
    d._add_entry(f2_frame, file2_var, 35).pack(side=tk.LEFT)
    tk.Button(f2_frame, text="Browse...",
              command=lambda: file2_var.set(filedialog.askopenfilename(
                  filetypes=[("PDF", "*.pdf")]) or file2_var.get()),
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(side=tk.LEFT, padx=4)

    def on_ok():
        f1 = file1_var.get()
        f2 = file2_var.get()
        if not f1 or not f2:
            messagebox.showwarning("Warning", "Please select both files.")
            return
        messagebox.showinfo("Compare", "Comparison would be performed here.")
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def form_field_dialog(editor):
    d = _DialogBase(editor, "Form Field Properties", "420x380")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X)

    field_types = ["text", "number", "checkbox", "dropdown", "date", "signature"]
    tk.Label(fields, text="Type:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    type_var = tk.StringVar(value="text")
    d._add_combobox(fields, type_var, field_types).grid(row=0, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Name:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    name_var = tk.StringVar()
    d._add_entry(fields, name_var).grid(row=1, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Default Value:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    value_var = tk.StringVar()
    d._add_entry(fields, value_var).grid(row=2, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Font Size:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=3, column=0, sticky="w", pady=4, padx=(0, 8))
    size_var = tk.IntVar(value=12)
    d._add_entry(fields, size_var, 10).grid(row=3, column=1, sticky="w", pady=4)

    required_var = tk.BooleanVar(value=False)
    d._add_checkbutton(fields, "Required", required_var).grid(
        row=4, column=0, columnspan=2, sticky="w", pady=4)

    fields.columnconfigure(1, weight=1)

    def on_ok():
        name = name_var.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Field name is required.")
            return
        elem = FormFieldElement(
            field_type=type_var.get(),
            field_name=name,
            value=value_var.get(),
            font_size=size_var.get(),
            required=required_var.get(),
            page=editor.current_page,
        )
        editor.undo_manager.save_state(editor.elements)
        editor.elements.append(elem)
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def header_footer_dialog(editor):
    d = _DialogBase(editor, "Header & Footer", "450x400")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X, pady=(0, 12))

    tk.Label(fields, text="Text:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    hf_text = tk.StringVar(value="{page} / {total}")
    d._add_entry(fields, hf_text, 30).grid(row=0, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Position:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    positions = [
        "header-left", "header-center", "header-right",
        "footer-left", "footer-center", "footer-right",
    ]
    pos_var = tk.StringVar(value="footer-center")
    d._add_combobox(fields, pos_var, positions).grid(row=1, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Font Size:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    hf_size = tk.IntVar(value=10)
    d._add_entry(fields, hf_size, 10).grid(row=2, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Color:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=3, column=0, sticky="w", pady=4, padx=(0, 8))
    hf_color = tk.StringVar(value="#666666")

    def pick_hf_color():
        c = colorchooser.askcolor(initialcolor=hf_color.get())[1]
        if c:
            hf_color.set(c)
            hf_color_btn.configure(bg=c)

    hf_color_btn = tk.Button(fields, text="Choose", bg=hf_color.get(), fg="white",
                             font=("Segoe UI", 8), relief="flat", cursor="hand2",
                             command=pick_hf_color)
    hf_color_btn.grid(row=3, column=1, sticky="w", pady=4)

    fields.columnconfigure(1, weight=1)

    tokens_frame = tk.Frame(d.content_frame, bg=BG)
    tokens_frame.pack(fill=tk.X, pady=(0, 12))
    tk.Label(tokens_frame, text="Tokens: {page} {total} {date} {filename}",
             bg=BG, fg="#a6adc8", font=("Segoe UI", 8)).pack(anchor="w")

    apply_var = tk.StringVar(value="all")
    apply_frame = tk.Frame(d.content_frame, bg=BG)
    apply_frame.pack(fill=tk.X)
    tk.Radiobutton(apply_frame, text="All Pages", variable=apply_var, value="all",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)
    tk.Radiobutton(apply_frame, text="Current Page", variable=apply_var, value="current",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)

    def on_ok():
        text = hf_text.get().strip()
        if not text:
            messagebox.showwarning("Warning", "Text cannot be empty.")
            return
        pages = range(editor.total_pages) if apply_var.get() == "all" else [editor.current_page]
        editor.undo_manager.save_state(editor.elements)
        for pg in pages:
            elem = HeaderFooterElement(
                text=text,
                size=hf_size.get(),
                color=hf_color.get(),
                position=pos_var.get(),
                page=pg,
            )
            editor.elements.append(elem)
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def about_dialog(editor):
    d = _DialogBase(editor, "About", "450x420")

    tk.Label(d.content_frame, text="PDF Editor Pro", bg=BG, fg=ACCENT,
             font=("Segoe UI", 18, "bold")).pack(pady=(20, 8))
    tk.Label(d.content_frame, text="Version 2.0", bg=BG, fg="#a6adc8",
             font=("Segoe UI", 10)).pack(pady=(0, 16))

    features = [
        "Text editing and formatting",
        "Image insertion and manipulation",
        "Shape drawing (rect, ellipse, triangle, line, arrow)",
        "Annotations (highlight, underline, strikethrough)",
        "Stamps and signatures",
        "Watermarks",
        "OCR text recognition",
        "PDF password protection",
        "Find & Replace",
        "Page management (insert, delete, rotate, reorder)",
        "Undo/Redo support",
        "Dark theme interface",
    ]

    feat_frame = tk.Frame(d.content_frame, bg=BG)
    feat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 16))
    tk.Label(feat_frame, text="Features:", bg=BG, fg=FG,
             font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
    for feat in features:
        tk.Label(feat_frame, text=f"\u2022 {feat}", bg=BG, fg=FG,
                 font=("Segoe UI", 9), anchor="w").pack(anchor="w", padx=8, pady=1)

    tk.Label(d.content_frame, text="Built with Python & Tkinter",
             bg=BG, fg="#a6adc8", font=("Segoe UI", 8)).pack(pady=(0, 8))

    def on_ok():
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()
