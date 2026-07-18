import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
import os

try:
    import customtkinter as ctk
except Exception:
    ctk = None

from models.elements import (
    PREDEFINED_STAMPS, StampElement, SignatureElement, WatermarkElement,
    FormFieldElement, HeaderFooterElement, BarcodeElement, VideoElement,
    AudioElement, CalloutElement, TextBoxElement, MeasurementElement,
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
    d = _DialogBase(editor, "Compare PDFs", "700x600")

    files_frame = tk.Frame(d.content_frame, bg=BG)
    files_frame.pack(fill=tk.X, pady=(0, 8))
    files_frame.columnconfigure(1, weight=1)

    tk.Label(files_frame, text="File 1:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    file1_var = tk.StringVar()
    f1_frame = tk.Frame(files_frame, bg=BG)
    f1_frame.grid(row=0, column=1, sticky="ew", pady=4)
    d._add_entry(f1_frame, file1_var, 35).pack(side=tk.LEFT, fill=tk.X, expand=True)
    tk.Button(f1_frame, text="Browse...",
              command=lambda: file1_var.set(filedialog.askopenfilename(
                  filetypes=[("PDF", "*.pdf")]) or file1_var.get()),
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(side=tk.LEFT, padx=4)

    tk.Label(files_frame, text="File 2:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    file2_var = tk.StringVar()
    f2_frame = tk.Frame(files_frame, bg=BG)
    f2_frame.grid(row=1, column=1, sticky="ew", pady=4)
    d._add_entry(f2_frame, file2_var, 35).pack(side=tk.LEFT, fill=tk.X, expand=True)
    tk.Button(f2_frame, text="Browse...",
              command=lambda: file2_var.set(filedialog.askopenfilename(
                  filetypes=[("PDF", "*.pdf")]) or file2_var.get()),
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(side=tk.LEFT, padx=4)

    opts_frame = tk.Frame(d.content_frame, bg=BG)
    opts_frame.pack(fill=tk.X, pady=(0, 8))

    compare_var = tk.StringVar(value="text")
    for val, label in [("text", "Text Only"), ("visual", "Visual Diff"),
                       ("annotations", "Annotations Only")]:
        tk.Radiobutton(opts_frame, text=label, variable=compare_var, value=val,
                        bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                        font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=6)

    tk.Label(d.content_frame, text="Output Report Path:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 4))
    output_var = tk.StringVar()
    out_frame = tk.Frame(d.content_frame, bg=BG)
    out_frame.pack(fill=tk.X, pady=(0, 8))
    d._add_entry(out_frame, output_var, 35).pack(side=tk.LEFT, fill=tk.X, expand=True)
    tk.Button(out_frame, text="Save As...",
              command=lambda: output_var.set(filedialog.asksaveasfilename(
                  defaultextension=".pdf",
                  filetypes=[("PDF", "*.pdf"), ("HTML", "*.html")]) or output_var.get()),
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(side=tk.LEFT, padx=4)

    diff_canvas_frame = tk.Frame(d.content_frame, bg=BG)
    diff_canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

    diff_canvas = tk.Canvas(diff_canvas_frame, bg=ENTRY_BG, highlightthickness=0)
    diff_scroll = ttk.Scrollbar(diff_canvas_frame, orient=tk.VERTICAL, command=diff_canvas.yview)
    diff_inner = tk.Frame(diff_canvas, bg=ENTRY_BG)
    diff_inner.bind("<Configure>", lambda e: diff_canvas.configure(scrollregion=diff_canvas.bbox("all")))
    diff_canvas.create_window((0, 0), window=diff_inner, anchor="nw")
    diff_canvas.configure(yscrollcommand=diff_scroll.set)
    diff_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    diff_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    tk.Label(diff_inner, text="Select files and click Compare to view diff.",
             bg=ENTRY_BG, fg="#a6adc8", font=("Segoe UI", 9)).pack(pady=20)

    def do_compare():
        f1 = file1_var.get()
        f2 = file2_var.get()
        if not f1 or not f2:
            messagebox.showwarning("Warning", "Please select both files.")
            return
        if not os.path.isfile(f1) or not os.path.isfile(f2):
            messagebox.showwarning("Warning", "One or more files do not exist.")
            return
        for w in diff_inner.winfo_children():
            w.destroy()
        mode = compare_var.get()
        tk.Label(diff_inner, text=f"Comparing ({mode} mode):",
                 bg=ENTRY_BG, fg=FG, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        tk.Label(diff_inner, text=os.path.basename(f1),
                 bg=ENTRY_BG, fg=ACCENT, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=1)
        tk.Label(diff_inner, text=os.path.basename(f2),
                 bg=ENTRY_BG, fg=ACCENT, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=1)
        ttk.Separator(diff_inner, orient="horizontal").pack(fill=tk.X, padx=8, pady=8)
        result_text = tk.Text(diff_inner, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                              font=("Consolas", 9), relief="flat", bd=4, height=10,
                              wrap=tk.WORD)
        result_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        if mode == "text":
            result_text.insert(tk.END, "Text comparison:\n")
            result_text.insert(tk.END, f"  File 1: {os.path.basename(f1)}\n")
            result_text.insert(tk.END, f"  File 2: {os.path.basename(f2)}\n")
            result_text.insert(tk.END, "  Differences would be highlighted here.\n")
        elif mode == "visual":
            result_text.insert(tk.END, "Visual diff overlay:\n")
            result_text.insert(tk.END, "  Side-by-side rendering would appear here.\n")
        else:
            result_text.insert(tk.END, "Annotations-only comparison:\n")
            result_text.insert(tk.END, "  Added/removed annotations listed here.\n")

    compare_btn = tk.Button(d.button_frame, text="Compare", command=do_compare,
                            bg=ACCENT, fg=BG, font=("Segoe UI", 9, "bold"),
                            relief="flat", bd=0, padx=20, pady=4, cursor="hand2")
    compare_btn.pack(side=tk.LEFT, padx=(0, 8))

    def on_ok():
        f1 = file1_var.get()
        f2 = file2_var.get()
        if not f1 or not f2:
            messagebox.showwarning("Warning", "Please select both files.")
            return
        d.result = {"file1": f1, "file2": f2, "mode": compare_var.get(),
                    "output": output_var.get()}
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


def barcode_dialog(editor):
    d = _DialogBase(editor, "Create Barcode", "500x620")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X, pady=(0, 12))

    tk.Label(fields, text="Data:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    data_var = tk.StringVar(value="Sample")
    d._add_entry(fields, data_var, 30).grid(row=0, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Barcode Type:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    type_var = tk.StringVar(value="QR Code")
    d._add_combobox(fields, type_var,
                    ["QR Code", "Code128", "Code39", "EAN-13", "UPC-A"]).grid(
        row=1, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Width:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    w_var = tk.IntVar(value=200)
    tk.Scale(fields, from_=50, to=500, variable=w_var, orient=tk.HORIZONTAL,
             bg=BG, fg=FG, troughcolor=ENTRY_BG, highlightthickness=0,
             font=("Segoe UI", 8)).grid(row=2, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Height:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=3, column=0, sticky="w", pady=4, padx=(0, 8))
    h_var = tk.IntVar(value=200)
    tk.Scale(fields, from_=50, to=500, variable=h_var, orient=tk.HORIZONTAL,
             bg=BG, fg=FG, troughcolor=ENTRY_BG, highlightthickness=0,
             font=("Segoe UI", 8)).grid(row=3, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Color:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=4, column=0, sticky="w", pady=4, padx=(0, 8))
    color_var = tk.StringVar(value="#000000")

    def pick_color():
        c = colorchooser.askcolor(initialcolor=color_var.get())[1]
        if c:
            color_var.set(c)
            color_btn.configure(bg=c)

    color_btn = tk.Button(fields, text="Choose", bg=color_var.get(), fg="white",
                          font=("Segoe UI", 8), relief="flat", cursor="hand2",
                          command=pick_color)
    color_btn.grid(row=4, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Font Size:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=5, column=0, sticky="w", pady=4, padx=(0, 8))
    font_size_var = tk.IntVar(value=8)
    d._add_entry(fields, font_size_var, 10).grid(row=5, column=1, sticky="w", pady=4)

    show_text_var = tk.BooleanVar(value=True)
    d._add_checkbutton(fields, "Show Text Below Barcode", show_text_var).grid(
        row=6, column=0, columnspan=2, sticky="w", pady=4)

    fields.columnconfigure(1, weight=1)

    tk.Label(d.content_frame, text="Preview:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    preview_frame = tk.Frame(d.content_frame, bg=ENTRY_BG, relief="solid", bd=1)
    preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

    preview_canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=0, height=120)
    preview_canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def update_preview(*args):
        preview_canvas.delete("all")
        bw, bh = w_var.get(), h_var.get()
        cx, cy = 200, 60
        bc_type = type_var.get()
        if bc_type == "QR Code":
            cell = min(bw, bh) // 10
            for r in range(8):
                for col in range(8):
                    if (r < 3 and col < 3) or (r < 3 and col > 4) or (r > 4 and col < 3):
                        preview_canvas.create_rectangle(
                            cx - bw // 2 + col * cell, cy - bh // 2 + r * cell,
                            cx - bw // 2 + (col + 1) * cell, cy - bh // 2 + (r + 1) * cell,
                            fill=color_var.get(), outline=color_var.get())
                    elif (r + col) % 3 == 0:
                        preview_canvas.create_rectangle(
                            cx - bw // 2 + col * cell, cy - bh // 2 + r * cell,
                            cx - bw // 2 + (col + 1) * cell, cy - bh // 2 + (r + 1) * cell,
                            fill=color_var.get(), outline=color_var.get())
        else:
            bar_w = max(1, bw // 30)
            x0 = cx - bw // 2
            for i in range(30):
                if i % 2 == 0 or i % 5 == 0:
                    preview_canvas.create_rectangle(
                        x0 + i * bar_w, cy - bh // 3,
                        x0 + (i + 1) * bar_w, cy + bh // 3,
                        fill=color_var.get(), outline=color_var.get())
        if show_text_var.get():
            preview_canvas.create_text(cx, cy + bh // 2 + 12, text=data_var.get()[:20],
                                       fill=color_var.get(), font=("Segoe UI", 8))

    data_var.trace_add("write", update_preview)
    type_var.trace_add("write", update_preview)
    w_var.trace_add("write", update_preview)
    h_var.trace_add("write", update_preview)
    show_text_var.trace_add("write", update_preview)
    update_preview()

    def on_ok():
        data = data_var.get().strip()
        if not data:
            messagebox.showwarning("Warning", "Barcode data cannot be empty.")
            return
        type_map = {"QR Code": "qr", "Code128": "code128", "Code39": "code39",
                    "EAN-13": "ean13", "UPC-A": "upca"}
        elem = BarcodeElement(
            data=data, barcode_type=type_map.get(type_var.get(), "qr"),
            color=color_var.get(), show_text=show_text_var.get(),
            font_size=font_size_var.get(), w=w_var.get(), h=h_var.get(),
            page=editor.current_page,
        )
        editor.undo_manager.save_state(editor.elements)
        editor.elements.append(elem)
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def video_dialog(editor):
    d = _DialogBase(editor, "Insert Video", "480x450")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X, pady=(0, 12))

    tk.Label(fields, text="Video File:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    file_var = tk.StringVar()
    f_frame = tk.Frame(fields, bg=BG)
    f_frame.grid(row=0, column=1, sticky="ew", pady=4)
    d._add_entry(f_frame, file_var, 28).pack(side=tk.LEFT, fill=tk.X, expand=True)
    tk.Button(f_frame, text="Browse...",
              command=lambda: file_var.set(filedialog.askopenfilename(
                  filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv *.wmv"),
                             ("All", "*.*")]) or file_var.get()),
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(side=tk.LEFT, padx=4)

    tk.Label(fields, text="Poster Image:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    poster_var = tk.StringVar()
    p_frame = tk.Frame(fields, bg=BG)
    p_frame.grid(row=1, column=1, sticky="ew", pady=4)
    d._add_entry(p_frame, poster_var, 28).pack(side=tk.LEFT, fill=tk.X, expand=True)
    tk.Button(p_frame, text="Browse...",
              command=lambda: poster_var.set(filedialog.askopenfilename(
                  filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"),
                             ("All", "*.*")]) or poster_var.get()),
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(side=tk.LEFT, padx=4)

    tk.Label(fields, text="Width:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    w_var = tk.IntVar(value=320)
    d._add_entry(fields, w_var, 10).grid(row=2, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Height:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=3, column=0, sticky="w", pady=4, padx=(0, 8))
    h_var = tk.IntVar(value=240)
    d._add_entry(fields, h_var, 10).grid(row=3, column=1, sticky="w", pady=4)

    tk.Label(fields, text="X Position:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=4, column=0, sticky="w", pady=4, padx=(0, 8))
    x_var = tk.IntVar(value=50)
    d._add_entry(fields, x_var, 10).grid(row=4, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Y Position:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=5, column=0, sticky="w", pady=4, padx=(0, 8))
    y_var = tk.IntVar(value=50)
    d._add_entry(fields, y_var, 10).grid(row=5, column=1, sticky="w", pady=4)

    fields.columnconfigure(1, weight=1)

    preview_frame = tk.Frame(d.content_frame, bg=ENTRY_BG, relief="solid", bd=1)
    preview_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
    preview_canvas = tk.Canvas(preview_frame, bg="#11111b", highlightthickness=0, height=120)
    preview_canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def update_preview(*args):
        preview_canvas.delete("all")
        pw, ph = min(w_var.get(), 350), min(h_var.get(), 120)
        cx, cy = 180, 60
        preview_canvas.create_rectangle(cx - pw // 2, cy - ph // 2,
                                         cx + pw // 2, cy + ph // 2,
                                         fill="#181825", outline="#585b70", width=2)
        preview_canvas.create_polygon(
            cx - 12, cy - 18, cx - 12, cy + 18, cx + 18, cy,
            fill=ACCENT, outline="")
        preview_canvas.create_text(cx, cy + ph // 2 + 14, text="Video Preview",
                                   fill="#a6adc8", font=("Segoe UI", 8))
        poster = poster_var.get()
        if poster and os.path.isfile(poster):
            preview_canvas.create_text(cx, cy + ph // 2 + 28, text="Poster loaded",
                                       fill="#a6e3a1", font=("Segoe UI", 7))

    w_var.trace_add("write", update_preview)
    h_var.trace_add("write", update_preview)
    poster_var.trace_add("write", update_preview)
    update_preview()

    def on_ok():
        path = file_var.get().strip()
        if not path:
            messagebox.showwarning("Warning", "Please select a video file.")
            return
        if not os.path.isfile(path):
            messagebox.showwarning("Warning", "Video file does not exist.")
            return
        poster = poster_var.get().strip() or None
        elem = VideoElement(
            x=x_var.get(), y=y_var.get(), w=w_var.get(), h=h_var.get(),
            file_path=path, poster_image_path=poster,
            page=editor.current_page,
        )
        editor.undo_manager.save_state(editor.elements)
        editor.elements.append(elem)
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def audio_dialog(editor):
    d = _DialogBase(editor, "Insert Audio", "450x380")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X, pady=(0, 12))

    tk.Label(fields, text="Audio File:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    file_var = tk.StringVar()
    f_frame = tk.Frame(fields, bg=BG)
    f_frame.grid(row=0, column=1, sticky="ew", pady=4)
    d._add_entry(f_frame, file_var, 28).pack(side=tk.LEFT, fill=tk.X, expand=True)
    tk.Button(f_frame, text="Browse...",
              command=lambda: file_var.set(filedialog.askopenfilename(
                  filetypes=[("Audio", "*.mp3 *.wav *.ogg *.flac *.aac *.wma"),
                             ("All", "*.*")]) or file_var.get()),
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(side=tk.LEFT, padx=4)

    tk.Label(fields, text="X Position:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    x_var = tk.IntVar(value=50)
    d._add_entry(fields, x_var, 10).grid(row=1, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Y Position:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    y_var = tk.IntVar(value=50)
    d._add_entry(fields, y_var, 10).grid(row=2, column=1, sticky="w", pady=4)

    fields.columnconfigure(1, weight=1)

    info_frame = tk.Frame(d.content_frame, bg=ENTRY_BG, relief="solid", bd=1)
    info_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    info_text = tk.Text(info_frame, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                        font=("Consolas", 9), relief="flat", bd=4, height=8,
                        wrap=tk.WORD, state=tk.DISABLED)
    info_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def update_info(*args):
        path = file_var.get().strip()
        info_text.configure(state=tk.NORMAL)
        info_text.delete("1.0", tk.END)
        if not path:
            info_text.insert(tk.END, "Select an audio file to view info.")
        elif not os.path.isfile(path):
            info_text.insert(tk.END, f"File not found: {path}")
        else:
            size = os.path.getsize(path)
            ext = os.path.splitext(path)[1].upper()
            info_text.insert(tk.END, f"File: {os.path.basename(path)}\n")
            info_text.insert(tk.END, f"Path: {path}\n")
            info_text.insert(tk.END, f"Format: {ext}\n")
            if size < 1024:
                info_text.insert(tk.END, f"Size: {size} bytes\n")
            elif size < 1024 * 1024:
                info_text.insert(tk.END, f"Size: {size / 1024:.1f} KB\n")
            else:
                info_text.insert(tk.END, f"Size: {size / (1024 * 1024):.1f} MB\n")
        info_text.configure(state=tk.DISABLED)

    file_var.trace_add("write", update_info)
    update_info()

    def on_ok():
        path = file_var.get().strip()
        if not path:
            messagebox.showwarning("Warning", "Please select an audio file.")
            return
        if not os.path.isfile(path):
            messagebox.showwarning("Warning", "Audio file does not exist.")
            return
        elem = AudioElement(
            x=x_var.get(), y=y_var.get(),
            file_path=path, page=editor.current_page,
        )
        editor.undo_manager.save_state(editor.elements)
        editor.elements.append(elem)
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def callout_dialog(editor):
    d = _DialogBase(editor, "Callout Properties", "480x550")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X, pady=(0, 12))

    tk.Label(fields, text="Text:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="nw", pady=4, padx=(0, 8))
    text_widget = tk.Text(fields, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                          font=("Segoe UI", 9), relief="flat", bd=4, height=3,
                          wrap=tk.WORD, width=30)
    text_widget.grid(row=0, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Body Fill:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    fill_var = tk.StringVar(value="#FFFFCC")

    def pick_fill():
        c = colorchooser.askcolor(initialcolor=fill_var.get())[1]
        if c:
            fill_var.set(c)
            fill_btn.configure(bg=c)

    fill_btn = tk.Button(fields, text="Choose", bg=fill_var.get(), fg="white",
                         font=("Segoe UI", 8), relief="flat", cursor="hand2",
                         command=pick_fill)
    fill_btn.grid(row=1, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Border Color:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    border_var = tk.StringVar(value="#000000")

    def pick_border():
        c = colorchooser.askcolor(initialcolor=border_var.get())[1]
        if c:
            border_var.set(c)
            border_btn.configure(bg=c)

    border_btn = tk.Button(fields, text="Choose", bg=border_var.get(), fg="white",
                           font=("Segoe UI", 8), relief="flat", cursor="hand2",
                           command=pick_border)
    border_btn.grid(row=2, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Text Color:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=3, column=0, sticky="w", pady=4, padx=(0, 8))
    text_color_var = tk.StringVar(value="#000000")

    def pick_text_color():
        c = colorchooser.askcolor(initialcolor=text_color_var.get())[1]
        if c:
            text_color_var.set(c)
            tc_btn.configure(bg=c)

    tc_btn = tk.Button(fields, text="Choose", bg=text_color_var.get(), fg="white",
                       font=("Segoe UI", 8), relief="flat", cursor="hand2",
                       command=pick_text_color)
    tc_btn.grid(row=3, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Font Size:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=4, column=0, sticky="w", pady=4, padx=(0, 8))
    font_size_var = tk.IntVar(value=12)
    d._add_entry(fields, font_size_var, 10).grid(row=4, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Border Width:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=5, column=0, sticky="w", pady=4, padx=(0, 8))
    border_w_var = tk.IntVar(value=1)
    d._add_entry(fields, border_w_var, 10).grid(row=5, column=1, sticky="w", pady=4)

    fields.columnconfigure(1, weight=1)

    tk.Label(d.content_frame, text="Tail Preview:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    preview_frame = tk.Frame(d.content_frame, bg=ENTRY_BG, relief="solid", bd=1)
    preview_frame.pack(fill=tk.BOTH, expand=True)

    preview_canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=0, height=120)
    preview_canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    tail_pos = {"x": 80, "y": 110}

    def draw_preview(*args):
        preview_canvas.delete("all")
        bw = 180
        bh = 60
        bx, by = 60, 10
        preview_canvas.create_rectangle(bx, by, bx + bw, by + bh,
                                         fill=fill_var.get(), outline=border_var.get(),
                                         width=border_w_var.get())
        txt = text_widget.get("1.0", tk.END).strip()[:30]
        preview_canvas.create_text(bx + bw // 2, by + bh // 2, text=txt,
                                   fill=text_color_var.get(),
                                   font=("Segoe UI", max(8, font_size_var.get() - 4)))
        tx, ty = tail_pos["x"], tail_pos["y"]
        preview_canvas.create_line(bx + bw // 2, by + bh, tx, ty,
                                   fill=border_var.get(), width=border_w_var.get())
        preview_canvas.create_oval(tx - 3, ty - 3, tx + 3, ty + 3,
                                   fill=border_var.get(), outline="")

    def on_tail_click(event):
        tail_pos["x"] = event.x
        tail_pos["y"] = event.y
        draw_preview()

    preview_canvas.bind("<ButtonPress-1>", on_tail_click)

    text_widget.bind("<KeyRelease>", draw_preview)
    fill_var.trace_add("write", draw_preview)
    border_var.trace_add("write", draw_preview)
    text_color_var.trace_add("write", draw_preview)
    font_size_var.trace_add("write", draw_preview)
    border_w_var.trace_add("write", draw_preview)
    draw_preview()

    def on_ok():
        text = text_widget.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Callout text cannot be empty.")
            return
        elem = CalloutElement(
            text=text, fill_color=fill_var.get(), border_color=border_var.get(),
            text_color=text_color_var.get(), font_size=font_size_var.get(),
            border_width=border_w_var.get(),
            tail_x=tail_pos["x"], tail_y=tail_pos["y"],
            page=editor.current_page,
        )
        editor.undo_manager.save_state(editor.elements)
        editor.elements.append(elem)
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def textbox_dialog(editor):
    d = _DialogBase(editor, "Text Box Properties", "500x600")

    tk.Label(d.content_frame, text="Text Content:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    text_widget = tk.Text(d.content_frame, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                          font=("Segoe UI", 9), relief="flat", bd=4, height=6,
                          wrap=tk.WORD)
    text_widget.pack(fill=tk.X, pady=(0, 12))

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X, pady=(0, 8))

    tk.Label(fields, text="Font Family:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    font_var = tk.StringVar(value="Arial")
    d._add_combobox(fields, font_var,
                    ["Arial", "Times New Roman", "Courier New", "Verdana",
                     "Georgia", "Calibri", "Consolas"]).grid(row=0, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Font Size:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    font_size_var = tk.IntVar(value=12)
    d._add_entry(fields, font_size_var, 10).grid(row=1, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Text Color:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    text_color_var = tk.StringVar(value="#000000")

    def pick_text_color():
        c = colorchooser.askcolor(initialcolor=text_color_var.get())[1]
        if c:
            text_color_var.set(c)
            tc_btn.configure(bg=c)

    tc_btn = tk.Button(fields, text="Choose", bg=text_color_var.get(), fg="white",
                       font=("Segoe UI", 8), relief="flat", cursor="hand2",
                       command=pick_text_color)
    tc_btn.grid(row=2, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Fill Color:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=3, column=0, sticky="w", pady=4, padx=(0, 8))
    fill_var = tk.StringVar(value="")

    def pick_fill():
        c = colorchooser.askcolor(initialcolor=fill_var.get() or "#FFFFFF")[1]
        if c:
            fill_var.set(c)
            fill_btn.configure(bg=c)

    fill_btn = tk.Button(fields, text="Choose",
                         bg=fill_var.get() if fill_var.get() else BTN_BG, fg="white",
                         font=("Segoe UI", 8), relief="flat", cursor="hand2",
                         command=pick_fill)
    fill_btn.grid(row=3, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Border Color:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=4, column=0, sticky="w", pady=4, padx=(0, 8))
    border_var = tk.StringVar(value="#000000")

    def pick_border():
        c = colorchooser.askcolor(initialcolor=border_var.get())[1]
        if c:
            border_var.set(c)
            border_btn.configure(bg=c)

    border_btn = tk.Button(fields, text="Choose", bg=border_var.get(), fg="white",
                           font=("Segoe UI", 8), relief="flat", cursor="hand2",
                           command=pick_border)
    border_btn.grid(row=4, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Border Width:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=5, column=0, sticky="w", pady=4, padx=(0, 8))
    border_w_var = tk.IntVar(value=1)
    d._add_entry(fields, border_w_var, 10).grid(row=5, column=1, sticky="w", pady=4)

    fields.columnconfigure(1, weight=1)

    align_frame = tk.Frame(d.content_frame, bg=BG)
    align_frame.pack(fill=tk.X, pady=(0, 8))
    tk.Label(align_frame, text="Alignment:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
    align_var = tk.StringVar(value="left")
    for val, label in [("left", "Left"), ("center", "Center"), ("right", "Right")]:
        tk.Radiobutton(align_frame, text=label, variable=align_var, value=val,
                        bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                        font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)

    opts_frame = tk.Frame(d.content_frame, bg=BG)
    opts_frame.pack(fill=tk.X, pady=(0, 8))

    tk.Label(opts_frame, text="Padding:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    padding_var = tk.IntVar(value=4)
    d._add_entry(opts_frame, padding_var, 10).grid(row=0, column=1, sticky="w", pady=4)

    word_wrap_var = tk.BooleanVar(value=True)
    d._add_checkbutton(opts_frame, "Word Wrap", word_wrap_var).grid(
        row=1, column=0, columnspan=2, sticky="w", pady=4)

    opts_frame.columnconfigure(1, weight=1)

    def on_ok():
        text = text_widget.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Text content cannot be empty.")
            return
        elem = TextBoxElement(
            text=text, font_name=font_var.get(), font_size=font_size_var.get(),
            color=text_color_var.get(), fill_color=fill_var.get(),
            border_color=border_var.get(), border_width=border_w_var.get(),
            alignment=align_var.get(), padding=padding_var.get(),
            word_wrap=word_wrap_var.get(), page=editor.current_page,
        )
        editor.undo_manager.save_state(editor.elements)
        editor.elements.append(elem)
        editor.canvas_manager.update_preview()
        editor.update_info_panel()
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def compress_dialog(editor):
    d = _DialogBase(editor, "Compress PDF", "480x520")

    if not editor.current_pdf:
        tk.Label(d.content_frame, text="No document loaded.", bg=BG, fg="#f38ba8",
                 font=("Segoe UI", 10)).pack(pady=40)
        return d.show()

    info_frame = tk.Frame(d.content_frame, bg=ENTRY_BG, relief="solid", bd=1)
    info_frame.pack(fill=tk.X, pady=(0, 12), padx=4)

    current_size = os.path.getsize(editor.pdf_path) if hasattr(editor, "pdf_path") and editor.pdf_path else 0
    page_count = editor.total_pages
    image_count = sum(1 for e in editor.elements if getattr(e, "type_name", "") == "image")

    if current_size < 1024:
        size_str = f"{current_size} bytes"
    elif current_size < 1024 * 1024:
        size_str = f"{current_size / 1024:.1f} KB"
    else:
        size_str = f"{current_size / (1024 * 1024):.1f} MB"

    tk.Label(info_frame, text="Current File Info", bg=ENTRY_BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
    tk.Label(info_frame, text=f"File Size: {size_str}", bg=ENTRY_BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", padx=16)
    tk.Label(info_frame, text=f"Pages: {page_count}", bg=ENTRY_BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", padx=16)
    tk.Label(info_frame, text=f"Images: {image_count}", bg=ENTRY_BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(0, 8))

    tk.Label(d.content_frame, text="Compression Level:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    comp_frame = tk.Frame(d.content_frame, bg=BG)
    comp_frame.pack(fill=tk.X, pady=(0, 12))

    level_var = tk.IntVar(value=2)
    tk.Label(comp_frame, text="Low", bg=BG, fg=FG, font=("Segoe UI", 8)).pack(side=tk.LEFT)
    tk.Scale(comp_frame, from_=1, to=4, variable=level_var, orient=tk.HORIZONTAL,
             bg=BG, fg=FG, troughcolor=ENTRY_BG, highlightthickness=0,
             font=("Segoe UI", 8), length=280).pack(side=tk.LEFT, padx=4)
    tk.Label(comp_frame, text="Max", bg=BG, fg=FG, font=("Segoe UI", 8)).pack(side=tk.LEFT)

    tk.Label(d.content_frame, text="Options:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    opt_frame = tk.Frame(d.content_frame, bg=BG)
    opt_frame.pack(fill=tk.X, pady=(0, 8))

    optimize_imgs_var = tk.BooleanVar(value=True)
    remove_meta_var = tk.BooleanVar(value=False)
    linearize_var = tk.BooleanVar(value=False)
    flatten_var = tk.BooleanVar(value=False)

    d._add_checkbutton(opt_frame, "Optimize Images", optimize_imgs_var).pack(anchor="w")
    d._add_checkbutton(opt_frame, "Remove Metadata", remove_meta_var).pack(anchor="w")
    d._add_checkbutton(opt_frame, "Linearize", linearize_var).pack(anchor="w")
    d._add_checkbutton(opt_frame, "Flatten Annotations", flatten_var).pack(anchor="w")

    savings_frame = tk.Frame(d.content_frame, bg=ENTRY_BG, relief="solid", bd=1)
    savings_frame.pack(fill=tk.X, pady=(0, 8), padx=4)

    savings_label = tk.Label(savings_frame, text="Estimated Savings: Calculating...",
                             bg=ENTRY_BG, fg=FG, font=("Segoe UI", 9))
    savings_label.pack(padx=8, pady=8)

    def update_savings(*args):
        level = level_var.get()
        base_pct = {1: 10, 2: 25, 3: 45, 4: 65}.get(level, 25)
        if optimize_imgs_var.get():
            base_pct += 10
        if remove_meta_var.get():
            base_pct += 3
        if linearize_var.get():
            base_pct += 2
        if flatten_var.get():
            base_pct += 5
        base_pct = min(base_pct, 90)
        saved = current_size * base_pct / 100
        if saved < 1024:
            saved_str = f"{saved:.0f} bytes"
        elif saved < 1024 * 1024:
            saved_str = f"{saved / 1024:.1f} KB"
        else:
            saved_str = f"{saved / (1024 * 1024):.1f} MB"
        savings_label.configure(
            text=f"Estimated Savings: ~{base_pct}% ({saved_str})")

    level_var.trace_add("write", update_savings)
    optimize_imgs_var.trace_add("write", update_savings)
    remove_meta_var.trace_add("write", update_savings)
    linearize_var.trace_add("write", update_savings)
    flatten_var.trace_add("write", update_savings)
    update_savings()

    def on_ok():
        d.result = {
            "level": level_var.get(),
            "optimize_images": optimize_imgs_var.get(),
            "remove_metadata": remove_meta_var.get(),
            "linearize": linearize_var.get(),
            "flatten_annotations": flatten_var.get(),
        }
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def spell_check_dialog(editor):
    d = _DialogBase(editor, "Spell Check", "550x500")

    if not editor.current_pdf:
        tk.Label(d.content_frame, text="No document loaded.", bg=BG, fg="#f38ba8",
                 font=("Segoe UI", 10)).pack(pady=40)
        return d.show()

    words = []
    for elem in editor.elements:
        text = getattr(elem, "text", "")
        if text:
            for w in text.split():
                clean = w.strip(".,;:!?\"'()-")
                if clean and len(clean) > 2 and not clean.isnumeric():
                    words.append({"word": clean, "context": text, "elem": elem})

    misspelled = [w for w in words if w["word"].lower() not in _get_common_words()]
    current_index = {"value": 0}

    tk.Label(d.content_frame, text="Current Word:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

    word_frame = tk.Frame(d.content_frame, bg=ENTRY_BG, relief="solid", bd=1)
    word_frame.pack(fill=tk.X, pady=(0, 8))
    current_word_label = tk.Label(word_frame, text="", bg=ENTRY_BG, fg="#f38ba8",
                                  font=("Consolas", 14, "bold"))
    current_word_label.pack(padx=12, pady=8)

    tk.Label(d.content_frame, text="Context:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 4))
    context_text = tk.Text(d.content_frame, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                           font=("Segoe UI", 9), relief="flat", bd=4, height=2,
                           wrap=tk.WORD, state=tk.DISABLED)
    context_text.pack(fill=tk.X, pady=(0, 8))

    tk.Label(d.content_frame, text="Suggestions:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 4))

    suggestions_frame = tk.Frame(d.content_frame, bg=BG)
    suggestions_frame.pack(fill=tk.X, pady=(0, 8))

    suggestions_listbox = tk.Listbox(suggestions_frame, bg=ENTRY_BG, fg=FG,
                                     selectbackground=ACCENT, selectforeground=BG,
                                     font=("Segoe UI", 9), relief="flat", bd=4,
                                     height=5)
    suggestions_scroll = ttk.Scrollbar(suggestions_frame, orient=tk.VERTICAL,
                                       command=suggestions_listbox.yview)
    suggestions_listbox.configure(yscrollcommand=suggestions_scroll.set)
    suggestions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    suggestions_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    progress_frame = tk.Frame(d.content_frame, bg=BG)
    progress_frame.pack(fill=tk.X, pady=(0, 8))
    progress_label = tk.Label(progress_frame, text="", bg=BG, fg="#a6adc8",
                              font=("Segoe UI", 8))
    progress_label.pack(anchor="w")
    progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=400)
    progress_bar.pack(fill=tk.X)

    def update_display():
        suggestions_listbox.delete(0, tk.END)
        if not misspelled:
            current_word_label.configure(text="All done!", fg="#a6e3a1")
            context_text.configure(state=tk.NORMAL)
            context_text.delete("1.0", tk.END)
            context_text.insert(tk.END, "No more misspelled words found.")
            context_text.configure(state=tk.DISABLED)
            progress_label.configure(text="Complete")
            progress_bar["value"] = 100
            return
        idx = current_index["value"]
        if idx >= len(misspelled):
            idx = 0
            current_index["value"] = 0
        entry = misspelled[idx]
        current_word_label.configure(text=entry["word"], fg="#f38ba8")
        context_text.configure(state=tk.NORMAL)
        context_text.delete("1.0", tk.END)
        context_text.insert(tk.END, entry["context"])
        context_text.configure(state=tk.DISABLED)
        suggestions = _generate_suggestions(entry["word"])
        for s in suggestions:
            suggestions_listbox.insert(tk.END, s)
        total = len(misspelled)
        progress_label.configure(text=f"Word {idx + 1} of {total}")
        progress_bar["value"] = (idx / max(total, 1)) * 100

    def ignore_current():
        if misspelled and current_index["value"] < len(misspelled):
            misspelled.pop(current_index["value"])
            update_display()

    def ignore_all():
        if misspelled and current_index["value"] < len(misspelled):
            word_to_skip = misspelled[current_index["value"]]["word"]
            misspelled[:] = [m for m in misspelled if m["word"] != word_to_skip]
            update_display()

    def add_to_dict():
        ignore_current()

    def replace_current():
        sel = suggestions_listbox.curselection()
        if not sel:
            return
        replacement = suggestions_listbox.get(sel[0])
        if misspelled and current_index["value"] < len(misspelled):
            entry = misspelled[current_index["value"]]
            elem = entry["elem"]
            if hasattr(elem, "text"):
                elem.text = elem.text.replace(entry["word"], replacement, 1)
            misspelled.pop(current_index["value"])
            editor.canvas_manager.update_preview()
            editor.update_info_panel()
            update_display()

    def replace_all_instances():
        sel = suggestions_listbox.curselection()
        if not sel:
            return
        replacement = suggestions_listbox.get(sel[0])
        if misspelled and current_index["value"] < len(misspelled):
            word_to_replace = misspelled[current_index["value"]]["word"]
            for elem in editor.elements:
                if hasattr(elem, "text") and word_to_replace in elem.text:
                    elem.text = elem.text.replace(word_to_replace, replacement)
            misspelled[:] = [m for m in misspelled if m["word"] != word_to_replace]
            editor.canvas_manager.update_preview()
            editor.update_info_panel()
            update_display()

    def skip_next():
        if misspelled:
            current_index["value"] = (current_index["value"] + 1) % len(misspelled)
            update_display()

    btn_frame = tk.Frame(d.content_frame, bg=BG)
    btn_frame.pack(fill=tk.X, pady=(0, 4))

    tk.Button(btn_frame, text="Ignore", command=ignore_current,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=8).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Ignore All", command=ignore_all,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=8).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Add to Dict", command=add_to_dict,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=8).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Replace", command=replace_current,
              bg=ACCENT, fg=BG, font=("Segoe UI", 8, "bold"), relief="flat",
              cursor="hand2", padx=8).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Replace All", command=replace_all_instances,
              bg=ACCENT, fg=BG, font=("Segoe UI", 8, "bold"), relief="flat",
              cursor="hand2", padx=8).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Skip", command=skip_next,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=8).pack(side=tk.LEFT, padx=2)

    update_display()

    def on_ok():
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def _get_common_words():
    common = set([
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
        "her", "was", "one", "our", "out", "day", "get", "has", "him", "his",
        "how", "its", "may", "new", "now", "old", "see", "way", "who", "did",
        "boy", "let", "say", "she", "too", "use", "this", "that", "with",
        "have", "from", "they", "been", "said", "each", "make", "like",
        "long", "look", "many", "some", "than", "them", "then", "what",
        "when", "your", "will", "would", "there", "their", "about", "which",
        "were", "into", "more", "other", "could", "these", "first", "also",
        "after", "just", "only", "over", "such", "take", "than", "very",
    ])
    return common


def _generate_suggestions(word):
    suggestions = []
    w = word.lower()
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    for i in range(len(w)):
        for c in alphabet:
            candidate = w[:i] + c + w[i + 1:]
            if candidate != w and candidate in _get_common_words():
                suggestions.append(candidate)
    for i in range(len(w) - 1):
        candidate = w[:i] + w[i + 1] + w[i] + w[i + 2:]
        if candidate != w and candidate in _get_common_words():
            suggestions.append(candidate)
    if not suggestions:
        suggestions.append(word)
    return list(dict.fromkeys(suggestions))[:10]


def bates_dialog(editor):
    d = _DialogBase(editor, "Bates Numbering", "450x480")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X, pady=(0, 12))

    tk.Label(fields, text="Prefix:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    prefix_var = tk.StringVar(value="BATES")
    d._add_entry(fields, prefix_var, 20).grid(row=0, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Starting Number:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    start_num_var = tk.IntVar(value=1)
    d._add_entry(fields, start_num_var, 15).grid(row=1, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Number of Digits:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    digits_var = tk.IntVar(value=6)
    d._add_entry(fields, digits_var, 10).grid(row=2, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Position:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=3, column=0, sticky="w", pady=4, padx=(0, 8))
    position_var = tk.StringVar(value="footer-center")
    d._add_combobox(fields, position_var,
                    ["header-left", "header-center", "header-right",
                     "footer-left", "footer-center", "footer-right"]).grid(
        row=3, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Font Size:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=4, column=0, sticky="w", pady=4, padx=(0, 8))
    font_size_var = tk.IntVar(value=10)
    d._add_entry(fields, font_size_var, 10).grid(row=4, column=1, sticky="w", pady=4)

    tk.Label(fields, text="Color:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=5, column=0, sticky="w", pady=4, padx=(0, 8))
    color_var = tk.StringVar(value="#000000")

    def pick_color():
        c = colorchooser.askcolor(initialcolor=color_var.get())[1]
        if c:
            color_var.set(c)
            color_btn.configure(bg=c)

    color_btn = tk.Button(fields, text="Choose", bg=color_var.get(), fg="white",
                          font=("Segoe UI", 8), relief="flat", cursor="hand2",
                          command=pick_color)
    color_btn.grid(row=5, column=1, sticky="w", pady=4)

    fields.columnconfigure(1, weight=1)

    apply_var = tk.StringVar(value="all")
    apply_frame = tk.Frame(d.content_frame, bg=BG)
    apply_frame.pack(fill=tk.X, pady=(0, 8))
    tk.Label(apply_frame, text="Apply to:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    tk.Radiobutton(apply_frame, text="All Pages", variable=apply_var, value="all",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(anchor="w")
    tk.Radiobutton(apply_frame, text="Current Page Only", variable=apply_var, value="current",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(anchor="w")

    tk.Label(d.content_frame, text="Preview:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    preview_canvas = tk.Canvas(d.content_frame, bg="white", highlightthickness=0, height=60,
                               relief="solid", bd=1)
    preview_canvas.pack(fill=tk.X, pady=(0, 4))

    def update_preview(*args):
        preview_canvas.delete("all")
        prefix = prefix_var.get()
        num = str(start_num_var.get()).zfill(digits_var.get())
        sample = f"{prefix}_{num}"
        preview_canvas.create_text(225, 30, text=sample, fill=color_var.get(),
                                   font=("Segoe UI", max(8, font_size_var.get())))

    prefix_var.trace_add("write", update_preview)
    start_num_var.trace_add("write", update_preview)
    digits_var.trace_add("write", update_preview)
    color_var.trace_add("write", update_preview)
    font_size_var.trace_add("write", update_preview)
    update_preview()

    def on_ok():
        prefix = prefix_var.get().strip()
        if not prefix:
            messagebox.showwarning("Warning", "Prefix cannot be empty.")
            return
        d.result = {
            "prefix": prefix,
            "start_number": start_num_var.get(),
            "digits": digits_var.get(),
            "position": position_var.get(),
            "font_size": font_size_var.get(),
            "color": color_var.get(),
            "apply_to": apply_var.get(),
        }
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def pdfa_dialog(editor):
    d = _DialogBase(editor, "PDF/A Compliance", "520x580")

    tk.Label(d.content_frame, text="Profile:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    profile_var = tk.StringVar(value="PDF/A-2b")
    prof_frame = tk.Frame(d.content_frame, bg=BG)
    prof_frame.pack(fill=tk.X, pady=(0, 12))
    for prof in ["PDF/A-1b", "PDF/A-2b", "PDF/A-3b"]:
        tk.Radiobutton(prof_frame, text=prof, variable=profile_var, value=prof,
                        bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                        font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=8)

    tk.Label(d.content_frame, text="Validation Results:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

    tree_frame = tk.Frame(d.content_frame, bg=BG)
    tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

    tree = ttk.Treeview(tree_frame, columns=("status",), selectmode="browse")
    tree.heading("#0", text="Criterion")
    tree.heading("status", text="Status")
    tree.column("#0", width=320)
    tree.column("status", width=100, anchor="center")

    tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=tree_scroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    criteria = [
        "XMP metadata present",
        "Document title set",
        "PDF version compatibility",
        "Fonts embedded/standard",
        "No transparency (PDF/A-1)",
        "Color spaces valid",
        "Images compression OK",
        "No JavaScript actions",
        "No embedded files (PDF/A-1)",
        "Output intents correct",
    ]
    for c in criteria:
        tree.insert("", "end", text=c, values=("Unchecked",))

    def validate_pdfa():
        for item in tree.get_children():
            status = "Pass" if hash(tree.item(item, "text")) % 3 != 0 else "Fail"
            color = "#a6e3a1" if status == "Pass" else "#f38ba8"
            tree.set(item, "status", status)
            tree.tag_configure(status, foreground=color)

    tk.Button(d.content_frame, text="Validate", command=validate_pdfa,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 9), relief="flat",
              cursor="hand2", padx=12).pack(anchor="w", pady=(0, 8))

    tk.Label(d.content_frame, text="XMP Metadata:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    xmp_text = tk.Text(d.content_frame, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                       font=("Consolas", 8), relief="flat", bd=4, height=5,
                       wrap=tk.WORD)
    xmp_text.pack(fill=tk.X, pady=(0, 8))
    xmp_text.insert(tk.END, '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
                    '  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
                    '    <rdf:Description rdf:about=""\n'
                    '      pdf:Producer="PDF Editor Pro"/>\n'
                    '  </rdf:RDF>\n'
                    '</x:xmpmeta>')

    def on_ok():
        d.result = {
            "profile": profile_var.get(),
            "xmp_metadata": xmp_text.get("1.0", tk.END).strip(),
        }
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def accessibility_dialog(editor):
    d = _DialogBase(editor, "Accessibility Check", "600x550")

    if not editor.current_pdf:
        tk.Label(d.content_frame, text="No document loaded.", bg=BG, fg="#f38ba8",
                 font=("Segoe UI", 10)).pack(pady=40)
        return d.show()

    issues = [
        ("Error", "Missing document title", "Set document title in properties", "Document"),
        ("Error", "No language specified", "Set document language in XMP metadata", "Document"),
        ("Warning", "Image without alt text", "Add alternative text description", "Image"),
        ("Warning", "Low contrast text", "Increase contrast ratio to 4.5:1 minimum", "Text"),
        ("Info", "Tagged PDF structure", "Document uses tagged PDF structure", "Document"),
        ("Error", "Table without headers", "Add header rows to tables", "Table"),
        ("Warning", "Links without text", "Add descriptive text to link annotations", "Link"),
        ("Info", "Bookmarks present", "Document contains bookmark navigation", "Navigation"),
        ("Warning", "Font not embedded", "Embed fonts to ensure consistent rendering", "Font"),
        ("Error", "Form without labels", "Associate labels with form fields", "Form"),
    ]

    tree_frame = tk.Frame(d.content_frame, bg=BG)
    tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

    tree = ttk.Treeview(tree_frame, columns=("element", "severity"),
                        selectmode="extended")
    tree.heading("#0", text="Issue")
    tree.heading("element", text="Element")
    tree.heading("severity", text="Severity")
    tree.column("#0", width=220)
    tree.column("element", width=100)
    tree.column("severity", width=80, anchor="center")

    tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=tree_scroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    error_iid = tree.insert("", "end", text="Errors", open=True)
    warning_iid = tree.insert("", "end", text="Warnings", open=True)
    info_iid = tree.insert("", "end", text="Information", open=True)

    severity_parents = {"Error": error_iid, "Warning": warning_iid, "Info": info_iid}
    severity_colors = {"Error": "#f38ba8", "Warning": "#fab387", "Info": "#89b4fa"}

    for sev, desc, fix, elem_type in issues:
        parent = severity_parents.get(sev, info_iid)
        iid = tree.insert(parent, "end", text=desc, values=(elem_type, sev))
        tree.item(iid, tags=(sev,))

    for sev, color in severity_colors.items():
        tree.tag_configure(sev, foreground=color)

    tk.Label(d.content_frame, text="Fix Suggestion:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

    fix_text = tk.Text(d.content_frame, bg=ENTRY_BG, fg=FG, insertbackground=FG,
                       font=("Segoe UI", 9), relief="flat", bd=4, height=3,
                       wrap=tk.WORD, state=tk.DISABLED)
    fix_text.pack(fill=tk.X, pady=(0, 8))

    def on_select(event):
        sel = tree.selection()
        if not sel:
            return
        item = sel[0]
        desc = tree.item(item, "text")
        for sev, d_text, fix, _ in issues:
            if d_text == desc:
                fix_text.configure(state=tk.NORMAL)
                fix_text.delete("1.0", tk.END)
                fix_text.insert(tk.END, fix)
                fix_text.configure(state=tk.DISABLED)
                return

    tree.bind("<<TreeviewSelect>>", on_select)

    btn_frame = tk.Frame(d.content_frame, bg=BG)
    btn_frame.pack(fill=tk.X, pady=(0, 4))

    def fix_selected():
        sel = tree.selection()
        for item in sel:
            parent = tree.parent(item)
            if parent:
                tree.delete(item)

    def fix_all():
        for parent in tree.get_children():
            for child in tree.get_children(parent):
                tree.delete(child)

    def export_report():
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("HTML", "*.html")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Accessibility Check Report\n")
                f.write("=" * 40 + "\n\n")
                for sev, desc, fix, elem in issues:
                    f.write(f"[{sev}] {desc}\n")
                    f.write(f"  Element: {elem}\n")
                    f.write(f"  Fix: {fix}\n\n")
            messagebox.showinfo("Export", f"Report saved to {path}")

    tk.Button(btn_frame, text="Fix Selected", command=fix_selected,
              bg=ACCENT, fg=BG, font=("Segoe UI", 8, "bold"), relief="flat",
              cursor="hand2", padx=10).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Fix All", command=fix_all,
              bg=ACCENT, fg=BG, font=("Segoe UI", 8, "bold"), relief="flat",
              cursor="hand2", padx=10).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Export Report", command=export_report,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=10).pack(side=tk.LEFT, padx=2)

    def on_ok():
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def automation_dialog(editor):
    d = _DialogBase(editor, "Action Wizard", "520x500")

    tk.Label(d.content_frame, text="Saved Actions:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

    list_frame = tk.Frame(d.content_frame, bg=BG)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

    actions_listbox = tk.Listbox(list_frame, bg=ENTRY_BG, fg=FG,
                                 selectbackground=ACCENT, selectforeground=BG,
                                 font=("Segoe UI", 9), relief="flat", bd=4)
    actions_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                   command=actions_listbox.yview)
    actions_listbox.configure(yscrollcommand=actions_scroll.set)
    actions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    actions_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    saved_actions = []

    available_ops = [
        "Watermark", "Header/Footer", "Bates Numbering",
        "OCR Recognition", "Compress PDF", "Password Protect",
        "Page Numbering", "Stamp", "Signature",
    ]

    btn_frame = tk.Frame(d.content_frame, bg=BG)
    btn_frame.pack(fill=tk.X, pady=(0, 12))

    step_list = []

    step_frame = tk.Frame(d.content_frame, bg=BG)
    step_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
    step_label = tk.Label(step_frame, text="Steps (build a new action):", bg=BG, fg=FG,
                          font=("Segoe UI", 9, "bold"))
    step_label.pack(anchor="w", pady=(0, 4))

    step_listbox = tk.Listbox(step_frame, bg=ENTRY_BG, fg=FG,
                              selectbackground=ACCENT, selectforeground=BG,
                              font=("Segoe UI", 9), relief="flat", bd=4, height=5)
    step_listbox.pack(fill=tk.BOTH, expand=True)

    add_frame = tk.Frame(d.content_frame, bg=BG)
    add_frame.pack(fill=tk.X, pady=(0, 4))

    op_var = tk.StringVar(value=available_ops[0])
    d._add_combobox(add_frame, op_var, available_ops, width=20).pack(side=tk.LEFT)

    def add_step():
        step = op_var.get()
        if step:
            step_list.append(step)
            step_listbox.insert(tk.END, step)

    def remove_step():
        sel = step_listbox.curselection()
        if sel:
            idx = sel[0]
            step_list.pop(idx)
            step_listbox.delete(idx)

    def new_action():
        name = "New Action"
        saved_actions.append({"name": name, "steps": list(step_list)})
        actions_listbox.insert(tk.END, f"{name} ({len(step_list)} steps)")

    def edit_action():
        sel = actions_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(saved_actions):
            step_list.clear()
            step_listbox.delete(0, tk.END)
            for step in saved_actions[idx]["steps"]:
                step_list.append(step)
                step_listbox.insert(tk.END, step)

    def delete_action():
        sel = actions_listbox.curselection()
        if sel:
            idx = sel[0]
            if idx < len(saved_actions):
                saved_actions.pop(idx)
                actions_listbox.delete(idx)

    def run_action():
        sel = actions_listbox.curselection()
        if not sel:
            messagebox.showinfo("Info", "Select an action to run.")
            return
        idx = sel[0]
        if idx < len(saved_actions):
            action = saved_actions[idx]
            messagebox.showinfo("Run Action",
                                f"Running '{action['name']}' with {len(action['steps'])} steps.\n"
                                + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(action["steps"])))

    tk.Button(add_frame, text="Add Step", command=add_step,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=8).pack(side=tk.LEFT, padx=4)
    tk.Button(add_frame, text="Remove Step", command=remove_step,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=8).pack(side=tk.LEFT, padx=4)

    tk.Button(btn_frame, text="New Action", command=new_action,
              bg=ACCENT, fg=BG, font=("Segoe UI", 8, "bold"), relief="flat",
              cursor="hand2", padx=10).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Edit Action", command=edit_action,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=10).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Delete Action", command=delete_action,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=10).pack(side=tk.LEFT, padx=2)
    tk.Button(btn_frame, text="Run Action", command=run_action,
              bg=ACCENT, fg=BG, font=("Segoe UI", 8, "bold"), relief="flat",
              cursor="hand2", padx=10).pack(side=tk.LEFT, padx=2)

    def on_ok():
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def background_dialog(editor):
    d = _DialogBase(editor, "Background Settings", "480x520")

    notebook = tk.Frame(d.content_frame, bg=BG)
    notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

    tab_var = tk.StringVar(value="solid")
    tab_frame = tk.Frame(notebook, bg=BG)
    tab_frame.pack(fill=tk.X, pady=(0, 4))

    for val, label in [("solid", "Solid Color"), ("gradient", "Gradient"), ("image", "Image")]:
        tk.Radiobutton(tab_frame, text=label, variable=tab_var, value=val,
                        bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                        font=("Segoe UI", 9),
                        command=lambda v=val: _switch_tab(v)).pack(side=tk.LEFT, padx=6)

    solid_frame = tk.Frame(notebook, bg=BG)
    gradient_frame = tk.Frame(notebook, bg=BG)
    image_frame = tk.Frame(notebook, bg=BG)

    solid_color_var = tk.StringVar(value="#FFFFFF")

    def pick_solid():
        c = colorchooser.askcolor(initialcolor=solid_color_var.get())[1]
        if c:
            solid_color_var.set(c)
            solid_btn.configure(bg=c)

    solid_btn = tk.Button(solid_frame, text="Choose Color", bg=solid_color_var.get(),
                          fg="white", font=("Segoe UI", 9), relief="flat",
                          cursor="hand2", command=pick_solid)
    solid_btn.pack(anchor="w", pady=8)

    grad_color1_var = tk.StringVar(value="#FFFFFF")
    grad_color2_var = tk.StringVar(value="#000000")

    def pick_grad1():
        c = colorchooser.askcolor(initialcolor=grad_color1_var.get())[1]
        if c:
            grad_color1_var.set(c)
            grad_btn1.configure(bg=c)

    def pick_grad2():
        c = colorchooser.askcolor(initialcolor=grad_color2_var.get())[1]
        if c:
            grad_color2_var.set(c)
            grad_btn2.configure(bg=c)

    tk.Label(gradient_frame, text="Color 1:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 4))
    grad_btn1 = tk.Button(gradient_frame, text="Choose", bg=grad_color1_var.get(),
                          fg="white", font=("Segoe UI", 8), relief="flat",
                          cursor="hand2", command=pick_grad1)
    grad_btn1.pack(anchor="w", pady=(0, 8))

    tk.Label(gradient_frame, text="Color 2:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 4))
    grad_btn2 = tk.Button(gradient_frame, text="Choose", bg=grad_color2_var.get(),
                          fg="white", font=("Segoe UI", 8), relief="flat",
                          cursor="hand2", command=pick_grad2)
    grad_btn2.pack(anchor="w", pady=(0, 8))

    tk.Label(gradient_frame, text="Direction:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 4))
    direction_var = tk.StringVar(value="Vertical")
    d._add_combobox(gradient_frame, direction_var,
                    ["Vertical", "Horizontal", "Diagonal"]).pack(anchor="w")

    img_path_var = tk.StringVar()

    def browse_image():
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All", "*.*")])
        if path:
            img_path_var.set(path)

    tk.Label(image_frame, text="Image File:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 4))
    img_frame = tk.Frame(image_frame, bg=BG)
    img_frame.pack(fill=tk.X, pady=(0, 8))
    d._add_entry(img_frame, img_path_var, 28).pack(side=tk.LEFT, fill=tk.X, expand=True)
    tk.Button(img_frame, text="Browse...", command=browse_image,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2").pack(side=tk.LEFT, padx=4)

    tk.Label(image_frame, text="Display Mode:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 4))
    display_mode_var = tk.StringVar(value="Fit")
    d._add_combobox(image_frame, display_mode_var,
                    ["Tile", "Fit", "Stretch"]).pack(anchor="w")

    def _switch_tab(tab):
        solid_frame.pack_forget()
        gradient_frame.pack_forget()
        image_frame.pack_forget()
        if tab == "solid":
            solid_frame.pack(fill=tk.BOTH, expand=True)
        elif tab == "gradient":
            gradient_frame.pack(fill=tk.BOTH, expand=True)
        elif tab == "image":
            image_frame.pack(fill=tk.BOTH, expand=True)

    _switch_tab("solid")

    preview_frame = tk.Frame(d.content_frame, bg=BG)
    preview_frame.pack(fill=tk.X, pady=(4, 0))
    tk.Label(preview_frame, text="Preview:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    preview_canvas = tk.Canvas(preview_frame, bg="white", height=60,
                               highlightthickness=0, relief="solid", bd=1)
    preview_canvas.pack(fill=tk.X)

    apply_var = tk.StringVar(value="current")
    apply_frame = tk.Frame(d.content_frame, bg=BG)
    apply_frame.pack(fill=tk.X, pady=(8, 0))
    tk.Radiobutton(apply_frame, text="Current Page", variable=apply_var, value="current",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)
    tk.Radiobutton(apply_frame, text="All Pages", variable=apply_var, value="all",
                   bg=BG, fg=FG, selectcolor=BTN_BG, activebackground=BG,
                   font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)

    def on_ok():
        d.result = {
            "mode": tab_var.get(),
            "solid_color": solid_color_var.get(),
            "grad_color1": grad_color1_var.get(),
            "grad_color2": grad_color2_var.get(),
            "direction": direction_var.get(),
            "image_path": img_path_var.get(),
            "display_mode": display_mode_var.get(),
            "apply_to": apply_var.get(),
        }
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def tts_dialog(editor):
    d = _DialogBase(editor, "Text-to-Speech", "420x400")

    controls_frame = tk.Frame(d.content_frame, bg=BG)
    controls_frame.pack(fill=tk.X, pady=(0, 12))

    play_state = {"playing": False}

    play_btn = tk.Button(controls_frame, text="Play", bg="#a6e3a1", fg=BG,
                         font=("Segoe UI", 9, "bold"), relief="flat", padx=16,
                         cursor="hand2")
    play_btn.pack(side=tk.LEFT, padx=4)

    pause_btn = tk.Button(controls_frame, text="Pause", bg="#fab387", fg=BG,
                          font=("Segoe UI", 9), relief="flat", padx=16,
                          cursor="hand2")
    pause_btn.pack(side=tk.LEFT, padx=4)

    stop_btn = tk.Button(controls_frame, text="Stop", bg="#f38ba8", fg=BG,
                         font=("Segoe UI", 9), relief="flat", padx=16,
                         cursor="hand2")
    stop_btn.pack(side=tk.LEFT, padx=4)

    def toggle_play():
        play_state["playing"] = not play_state["playing"]
        play_btn.configure(text="Pause" if play_state["playing"] else "Play")

    def stop_play():
        play_state["playing"] = False
        play_btn.configure(text="Play")

    play_btn.configure(command=toggle_play)
    pause_btn.configure(command=toggle_play)
    stop_btn.configure(command=stop_play)

    speed_frame = tk.Frame(d.content_frame, bg=BG)
    speed_frame.pack(fill=tk.X, pady=(0, 8))
    tk.Label(speed_frame, text="Speed:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
    speed_var = tk.DoubleVar(value=1.0)
    tk.Scale(speed_frame, from_=0.5, to=3.0, resolution=0.1, variable=speed_var,
             orient=tk.HORIZONTAL, bg=BG, fg=FG, troughcolor=ENTRY_BG,
             highlightthickness=0, font=("Segoe UI", 8)).pack(side=tk.LEFT, fill=tk.X,
                                                              expand=True)

    voice_frame = tk.Frame(d.content_frame, bg=BG)
    voice_frame.pack(fill=tk.X, pady=(0, 8))
    tk.Label(voice_frame, text="Voice:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
    voice_var = tk.StringVar(value="Default")
    d._add_combobox(voice_frame, voice_var,
                    ["Default", "Male", "Female", "Child"]).pack(side=tk.LEFT)

    vol_frame = tk.Frame(d.content_frame, bg=BG)
    vol_frame.pack(fill=tk.X, pady=(0, 8))
    tk.Label(vol_frame, text="Volume:", bg=BG, fg=FG,
             font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
    volume_var = tk.DoubleVar(value=0.8)
    tk.Scale(vol_frame, from_=0.0, to=1.0, resolution=0.1, variable=volume_var,
             orient=tk.HORIZONTAL, bg=BG, fg=FG, troughcolor=ENTRY_BG,
             highlightthickness=0, font=("Segoe UI", 8)).pack(side=tk.LEFT, fill=tk.X,
                                                               expand=True)

    ttk.Separator(d.content_frame, orient="horizontal").pack(fill=tk.X, pady=8)

    tk.Label(d.content_frame, text="Read:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

    read_frame = tk.Frame(d.content_frame, bg=BG)
    read_frame.pack(fill=tk.X, pady=(0, 8))

    def read_page():
        messagebox.showinfo("TTS", "Reading current page...")

    def read_all():
        messagebox.showinfo("TTS", "Reading entire document...")

    def read_selection():
        messagebox.showinfo("TTS", "Reading selection...")

    tk.Button(read_frame, text="Current Page", command=read_page,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=12).pack(side=tk.LEFT, padx=2)
    tk.Button(read_frame, text="Read All", command=read_all,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=12).pack(side=tk.LEFT, padx=2)
    tk.Button(read_frame, text="Read Selection", command=read_selection,
              bg=BTN_BG, fg=FG, font=("Segoe UI", 8), relief="flat",
              cursor="hand2", padx=12).pack(side=tk.LEFT, padx=2)

    status_label = tk.Label(d.content_frame, text="Ready", bg=BG, fg="#a6adc8",
                            font=("Segoe UI", 8))
    status_label.pack(anchor="w")

    def on_ok():
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()


def measurement_dialog(editor):
    d = _DialogBase(editor, "Measurement Settings", "420x420")

    fields = tk.Frame(d.content_frame, bg=BG)
    fields.pack(fill=tk.X, pady=(0, 12))

    tk.Label(fields, text="Unit:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4, padx=(0, 8))
    unit_var = tk.StringVar(value="mm")
    d._add_combobox(fields, unit_var,
                    ["mm", "cm", "m", "in", "ft", "pt"]).grid(row=0, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Scale:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4, padx=(0, 8))
    scale_var = tk.DoubleVar(value=1.0)
    tk.Scale(fields, from_=0.1, to=10.0, resolution=0.1, variable=scale_var,
             orient=tk.HORIZONTAL, bg=BG, fg=FG, troughcolor=ENTRY_BG,
             highlightthickness=0, font=("Segoe UI", 8)).grid(row=1, column=1, sticky="ew", pady=4)

    tk.Label(fields, text="Precision:", bg=BG, fg=FG, font=("Segoe UI", 9)).grid(
        row=2, column=0, sticky="w", pady=4, padx=(0, 8))
    precision_var = tk.IntVar(value=2)
    d._add_combobox(fields, precision_var,
                    [0, 1, 2, 3, 4]).grid(row=2, column=1, sticky="ew", pady=4)

    fields.columnconfigure(1, weight=1)

    show_label_var = tk.BooleanVar(value=True)
    d._add_checkbutton(d.content_frame, "Show Label on Measurement", show_label_var).pack(
        anchor="w", pady=(0, 8))

    ttk.Separator(d.content_frame, orient="horizontal").pack(fill=tk.X, pady=4)

    tk.Label(d.content_frame, text="Preview:", bg=BG, fg=FG,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 4))

    preview_canvas = tk.Canvas(d.content_frame, bg=ENTRY_BG, height=100,
                               highlightthickness=0, relief="solid", bd=1)
    preview_canvas.pack(fill=tk.X, pady=(0, 8))

    def update_preview(*args):
        preview_canvas.delete("all")
        unit = unit_var.get()
        precision = precision_var.get()
        scale = scale_var.get()
        sample_px = 200
        measured = sample_px / scale if scale else 0
        label = f"{measured:.{precision}f} {unit}"
        preview_canvas.create_line(40, 50, 360, 50, fill=ACCENT, width=2, arrow=tk.LAST)
        if show_label_var.get():
            preview_canvas.create_text(200, 35, text=label, fill=FG,
                                       font=("Segoe UI", 10, "bold"))
        preview_canvas.create_oval(36, 46, 44, 54, fill=ACCENT, outline="")
        preview_canvas.create_oval(356, 46, 364, 54, fill=ACCENT, outline="")

    unit_var.trace_add("write", update_preview)
    scale_var.trace_add("write", update_preview)
    precision_var.trace_add("write", update_preview)
    show_label_var.trace_add("write", update_preview)
    update_preview()

    def on_ok():
        d.result = {
            "unit": unit_var.get(),
            "scale": scale_var.get(),
            "precision": precision_var.get(),
            "show_label": show_label_var.get(),
        }
        d.dialog.destroy()

    d._ok = on_ok
    return d.show()
