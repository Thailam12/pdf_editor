import tkinter as tk
from tkinter import ttk, colorchooser, messagebox

try:
    import customtkinter as ctk
except Exception:
    ctk = None


BG = "#1e1e2e"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
BTN_BG = "#45475a"
BTN_FG = "#cdd6f4"
ACTIVE_BG = "#585b70"
HOVER_BG = "#585b70"
TAB_BG = "#313244"
SEPARATOR_BG = "#585b70"
DROPDOWN_BG = "#313244"
CANVAS_BG = "#181825"


def _make_button(parent, text, command=None, **kw):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=kw.pop("bg", BTN_BG),
        fg=kw.pop("fg", BTN_FG),
        activebackground=kw.pop("activebackground", ACTIVE_BG),
        activeforeground=kw.pop("activeforeground", FG),
        relief=kw.pop("relief", "flat"),
        bd=kw.pop("bd", 0),
        font=kw.pop("font", ("Segoe UI", 9)),
        cursor=kw.pop("cursor", "hand2"),
        padx=kw.pop("padx", 6),
        pady=kw.pop("pady", 3),
        width=kw.pop("width", None),
        anchor=kw.pop("anchor", "center"),
    )
    btn.pack_configure(**{k: v for k, v in kw.items() if k in ("side", "padx", "pady", "fill", "expand")})
    btn.bind("<Enter>", lambda e: btn.configure(bg=HOVER_BG) if btn["state"] != "disabled" else None)
    btn.bind("<Leave>", lambda e: btn.configure(bg=BTN_BG) if btn["state"] != "disabled" else None)
    return btn


def _make_small_button(parent, text, command=None):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=BTN_BG,
        fg=BTN_FG,
        activebackground=ACTIVE_BG,
        activeforeground=FG,
        relief="flat",
        bd=0,
        font=("Segoe UI", 8),
        cursor="hand2",
        padx=4,
        pady=2,
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=HOVER_BG) if btn["state"] != "disabled" else None)
    btn.bind("<Leave>", lambda e: btn.configure(bg=BTN_BG) if btn["state"] != "disabled" else None)
    return btn


class RibbonGroup(tk.Frame):
    def __init__(self, parent, label, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.label_frame = tk.Frame(self, bg=BG)
        self.label_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=1)
        self.btn_frame = tk.Frame(self.label_frame, bg=BG)
        self.btn_frame.pack(fill=tk.BOTH, expand=True)
        self.bottom_label = tk.Label(
            self.label_frame,
            text=label,
            bg=BG,
            fg="#a6adc8",
            font=("Segoe UI", 7),
            anchor="center",
        )
        self.bottom_label.pack(side=tk.BOTTOM, fill=tk.X)

    def add_button(self, text, command=None, **kw):
        btn = _make_small_button(self.btn_frame, text, command)
        btn.pack(side=kw.pop("side", tk.LEFT), padx=1, pady=1, anchor="n")
        return btn

    def add_button_grid(self, text, command=None, row=0, col=0, **kw):
        btn = _make_small_button(self.btn_frame, text, command)
        btn.grid(row=row, column=col, padx=1, pady=1, sticky="nsew", **kw)
        return btn


class _DropdownMenu:
    def __init__(self, parent_btn, items, command):
        self.parent_btn = parent_btn
        self.items = items
        self.command = command
        self.menu = None
        self._showing = False
        parent_btn.bind("<Button-1>", self._toggle)

    def _toggle(self, event=None):
        if self._showing:
            self._hide()
        else:
            self._show()

    def _show(self):
        if self.menu is not None:
            self._hide()
        self.menu = tk.Menu(
            self.parent_btn,
            tearoff=0,
            bg=DROPDOWN_BG,
            fg=FG,
            activebackground=ACCENT,
            activeforeground=BG,
            relief="flat",
            font=("Segoe UI", 9),
        )
        for item_text, cmd in self.items:
            if item_text == "---":
                self.menu.add_separator()
            else:
                self.menu.add_command(label=item_text, command=lambda c=cmd: self._run(c))
        x = self.parent_btn.winfo_rootx()
        y = self.parent_btn.winfo_rooty() + self.parent_btn.winfo_height()
        try:
            self.menu.tk_popup(x, y)
            self._showing = True
            self.menu.bind("<Unmap>", lambda e: self._on_unmap())
        except Exception:
            pass

    def _on_unmap(self):
        self._showing = False
        self.menu = None

    def _hide(self):
        if self.menu:
            try:
                self.menu.grab_release()
            except Exception:
                pass
            self.menu.destroy()
            self.menu = None
            self._showing = False

    def _run(self, cmd):
        self._hide()
        if cmd:
            cmd()


class RibbonDropdown(tk.Frame):
    def __init__(self, parent, label, items, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.btn = tk.Button(
            self,
            text=label + " \u25be",
            bg=BTN_BG,
            fg=BTN_FG,
            activebackground=ACTIVE_BG,
            activeforeground=FG,
            relief="flat",
            bd=0,
            font=("Segoe UI", 8),
            cursor="hand2",
            padx=4,
            pady=2,
        )
        self.btn.pack(side=tk.LEFT)
        self.btn.bind("<Enter>", lambda e: self.btn.configure(bg=HOVER_BG))
        self.btn.bind("<Leave>", lambda e: self.btn.configure(bg=BTN_BG))
        self._dropdown = _DropdownMenu(self.btn, items, None)
        self._menu = None

    def set_command(self, command):
        self._dropdown._show = lambda: self._show_menu(command)

    def _show_menu(self, command):
        if self._menu is not None:
            self._menu.destroy()
        self._menu = tk.Menu(
            self.btn,
            tearoff=0,
            bg=DROPDOWN_BG,
            fg=FG,
            activebackground=ACCENT,
            activeforeground=BG,
            relief="flat",
            font=("Segoe UI", 9),
        )
        for item_text, cmd in self._dropdown.items:
            if item_text == "---":
                self._menu.add_separator()
            else:
                self._menu.add_command(label=item_text, command=lambda c=cmd: self._run_menu(c))
        x = self.btn.winfo_rootx()
        y = self.btn.winfo_rooty() + self.btn.winfo_height()
        try:
            self._menu.tk_popup(x, y)
        except Exception:
            pass

    def _run_menu(self, cmd):
        if self._menu:
            self._menu.destroy()
            self._menu = None
        if cmd:
            cmd()


def _add_separator(parent, orient=tk.VERTICAL):
    sep = tk.Frame(parent, bg=SEPARATOR_BG, width=2)
    sep.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)
    return sep


def _add_hseparator(parent):
    sep = tk.Frame(parent, bg=SEPARATOR_BG, height=2)
    sep.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)
    return sep


def create_ribbon(editor, parent):
    ribbon_frame = tk.Frame(parent, bg=BG, bd=0, highlightthickness=0)
    ribbon_frame.pack(side=tk.TOP, fill=tk.X)

    tab_bar = tk.Frame(ribbon_frame, bg=BG, bd=0)
    tab_bar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4, 0))

    panels_container = tk.Frame(ribbon_frame, bg=BG, bd=0)
    panels_container.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(0, 2))

    tabs = {}
    tab_buttons = {}
    active_tab = tk.StringVar(value="Home")

    def switch_tab(name):
        active_tab.set(name)
        for t_name, panel in tabs.items():
            if t_name == name:
                panel.pack(fill=tk.BOTH, expand=True)
            else:
                panel.pack_forget()
        for t_name, btn in tab_buttons.items():
            if t_name == name:
                btn.configure(bg=ACCENT, fg=BG)
            else:
                btn.configure(bg=BG, fg=FG)

    tab_names = ["File", "Home", "Insert", "Annotate", "Page", "View", "Tools", "Help"]
    for tname in tab_names:
        panel = tk.Frame(panels_container, bg=BG, bd=0)
        tabs[tname] = panel

        btn = tk.Button(
            tab_bar,
            text=tname,
            command=lambda n=tname: switch_tab(n),
            bg=BG,
            fg=FG,
            activebackground=ACTIVE_BG,
            activeforeground=FG,
            relief="flat",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
        )
        btn.pack(side=tk.LEFT, padx=1)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=ACTIVE_BG) if active_tab.get() != cget_text(b) else None)
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=BG) if active_tab.get() != cget_text(b) else None)
        tab_buttons[tname] = btn

    def cget_text(b):
        return b.cget("text")

    def _build_file_tab(panel):
        g = RibbonGroup(panel, "File")
        g.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g.add_button("\U0001f4c4 New", editor.new_temp_document)
        g.add_button("\U0001f4c2 Open", editor.open_pdf)
        g.add_button("\U0001f4be Save", editor.save_pdf)
        g.add_button("\U0001f4cb Save As", editor.save_as_pdf)
        _add_separator(panel)
        g2 = RibbonGroup(panel, "Output")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\U0001f5a8 Print", editor.print_pdf)
        g2.add_button("\U0001f4e4 Export", editor.export_pdf)
        _add_separator(panel)
        g3 = RibbonGroup(panel, "Close")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\U0001f512 Close", editor.root.quit)

    def _build_home_tab(panel):
        g1 = RibbonGroup(panel, "Clipboard")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\u2702 Cut", lambda: editor.root.event_generate("<<Cut>>"))
        g1.add_button("\U0001f4cb Copy", lambda: editor.root.event_generate("<<Copy>>"))
        g1.add_button("\U0001f4ea Paste", lambda: editor.root.event_generate("<<Paste>>"))

        _add_separator(panel)

        g2 = RibbonGroup(panel, "Undo")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\u21b6 Undo", editor.undo)
        g2.add_button("\u21b7 Redo", editor.redo)

        _add_separator(panel)

        g3 = RibbonGroup(panel, "Tools")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\U0001f5c1 Select", editor.toggle_selection_mode)
        g3.add_button("\U0001f520 Text", editor.add_text)
        g3.add_button("\U0001f5bc Image", editor.add_image)
        shape_items = [
            ("\u25a1 Rectangle", lambda: editor.start_drawing("rect")),
            ("\u25cb Ellipse", lambda: editor.start_drawing("ellipse")),
            ("\u25b3 Triangle", lambda: editor.start_drawing("triangle")),
            ("\u2571 Line", lambda: editor.start_drawing("line")),
            ("\u2192 Arrow", lambda: editor.start_drawing("arrow")),
        ]
        shape_btn = g3.add_button("\u2b21 Shape \u25be")
        shape_menu = _DropdownMenu(shape_btn, shape_items, None)
        shape_menu.command = None

        _add_separator(panel)

        g4 = RibbonGroup(panel, "Font")
        g4.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g4.btn_frame.columnconfigure(0, weight=1)
        g4.btn_frame.columnconfigure(1, weight=0)

        font_frame = tk.Frame(g4.btn_frame, bg=BG)
        font_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=1, pady=1)
        tk.Label(font_frame, text="Font:", bg=BG, fg=FG, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)
        font_var = tk.StringVar(value="Arial")
        font_combo = ttk.Combobox(font_frame, textvariable=font_var,
                                  values=["Arial", "Times New Roman", "Courier", "Calibri", "Verdana"],
                                  width=12, state="readonly")
        font_combo.pack(side=tk.LEFT, padx=2)
        font_combo.bind("<<ComboboxSelected>>", lambda e: editor.set_font(font_var.get()))
        editor.font_var = font_var

        size_frame = tk.Frame(g4.btn_frame, bg=BG)
        size_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=1, pady=1)
        tk.Label(size_frame, text="Size:", bg=BG, fg=FG, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)
        size_var = tk.IntVar(value=12)
        size_combo = ttk.Combobox(size_frame, textvariable=size_var,
                                  values=[8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 48, 72],
                                  width=5, state="readonly")
        size_combo.pack(side=tk.LEFT, padx=2)
        size_combo.bind("<<ComboboxSelected>>", lambda e: editor.set_font_size(size_var.get()))
        editor.size_var = size_var

        style_frame = tk.Frame(g4.btn_frame, bg=BG)
        style_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=1, pady=1)
        bold_btn = tk.Button(style_frame, text="B", command=editor.toggle_bold,
                             bg=BTN_BG, fg=BTN_FG, font=("Segoe UI", 9, "bold"),
                             width=3, relief="flat", bd=0, cursor="hand2")
        bold_btn.pack(side=tk.LEFT, padx=1)
        editor.bold_btn = bold_btn
        italic_btn = tk.Button(style_frame, text="I", command=editor.toggle_italic,
                               bg=BTN_BG, fg=BTN_FG, font=("Segoe UI", 9, "italic"),
                               width=3, relief="flat", bd=0, cursor="hand2")
        italic_btn.pack(side=tk.LEFT, padx=1)
        editor.italic_btn = italic_btn
        underline_btn = tk.Button(style_frame, text="U", command=editor.toggle_underline,
                                  bg=BTN_BG, fg=BTN_FG, font=("Segoe UI", 9, "underline"),
                                  width=3, relief="flat", bd=0, cursor="hand2")
        underline_btn.pack(side=tk.LEFT, padx=1)
        editor.underline_btn = underline_btn

        g4.add_button("\U0001f3a8 Color", editor.pick_color)

        _add_separator(panel)

        g5 = RibbonGroup(panel, "Align")
        g5.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g5.add_button("\u25c0", lambda: editor.set_alignment("left"))
        g5.add_button("\u25ec", lambda: editor.set_alignment("center"))
        g5.add_button("\u25b6", lambda: editor.set_alignment("right"))

        _add_separator(panel)

        g6 = RibbonGroup(panel, "Edit")
        g6.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g6.add_button("\u2716 Delete", editor.delete_selected_element)
        g6.add_button("\u2716 Clear", editor.clear_elements)

    def _build_insert_tab(panel):
        g1 = RibbonGroup(panel, "Elements")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\U0001f520 Text Box", editor.add_text)
        g1.add_button("\U0001f5bc Image", editor.add_image)
        g1.add_button("\u2b21 Shape", lambda: editor.start_drawing("rect"))

        _add_separator(panel)

        g2 = RibbonGroup(panel, "Special")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\U0001f4ac Stamp", lambda: None)
        g2.add_button("\u270d Signature", lambda: None)
        g2.add_button("\U0001f517 Link", lambda: None)
        g2.add_button("\u2602 Watermark", lambda: None)

        _add_separator(panel)

        g3 = RibbonGroup(panel, "Document")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\U0001f4dd Header/Footer", lambda: None)
        g3.add_button("\U0001f4ce Attachment", lambda: None)
        g3.add_button("\U0001f4dd Form Field", lambda: None)
        g3.add_button("\U0001f4c4 Page No.", lambda: None)

    def _build_annotate_tab(panel):
        g1 = RibbonGroup(panel, "Highlight")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\U0001f4dd Highlight", lambda: editor.start_drawing("highlight"))
        g1.add_button("\u0332 Underline", lambda: None)
        g1.add_button("\u0336 Strikethrough", lambda: None)
        g1.add_button("\u0332 Squiggly", lambda: None)

        _add_separator(panel)

        g2 = RibbonGroup(panel, "Notes")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\U0001f4ac Sticky Note", lambda: None)
        g2.add_button("\U0001f520 Text Box", editor.add_text)

        _add_separator(panel)

        g3 = RibbonGroup(panel, "Draw")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\u270d Freehand", lambda: editor.start_drawing("freehand"))
        g3.add_button("\U0001f9f9 Eraser", lambda: None)
        g3.add_button("\U0001f4ac Stamp", lambda: None)

    def _build_page_tab(panel):
        g1 = RibbonGroup(panel, "Pages")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\u2795 Insert", lambda: None)
        g1.add_button("\u2796 Delete", lambda: None)
        g1.add_button("\u2b06 Move", lambda: None)
        g1.add_button("\u2398 Duplicate", lambda: None)

        _add_separator(panel)

        g2 = RibbonGroup(panel, "Rotate")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\U0001f504 CW", lambda: None)
        g2.add_button("\U0001f504 CCW", lambda: None)

        _add_separator(panel)

        g3 = RibbonGroup(panel, "Layout")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\u2702 Crop", lambda: None)
        g3.add_button("\u21f5 Resize", lambda: None)
        g3.add_button("\U0001f4d0 Merge", lambda: None)
        g3.add_button("\u2702 Split", lambda: None)

    def _build_view_tab(panel):
        g1 = RibbonGroup(panel, "Zoom")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\U0001f50d +", lambda: editor.set_zoom(editor.zoom_level + 10))
        g1.add_button("\U0001f50e -", lambda: editor.set_zoom(editor.zoom_level - 10))
        g1.add_button("\U0001f4d0 Fit", lambda: editor.set_zoom(100))
        g1.add_button("\u21f4 Width", lambda: editor.set_zoom(100))

        _add_separator(panel)

        g2 = RibbonGroup(panel, "Layout")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\u258c Single", lambda: None)
        g2.add_button("\u2583\u2583 Facing", lambda: None)
        g2.add_button("\u21f5 Cont.", lambda: None)

        _add_separator(panel)

        g3 = RibbonGroup(panel, "Display")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\u2b1a Grid", lambda: None)
        g3.add_button("\u21f5 Rulers", lambda: None)
        g3.add_button("\U0001f319 Dark", lambda: None)

    def _build_tools_tab(panel):
        g1 = RibbonGroup(panel, "PDF Tools")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\U0001f4d6 OCR", editor.ocr_current_page_dialog)
        g1.add_button("\u2b1a Redact", lambda: None)
        g1.add_button("\U0001f50d Compare", lambda: None)
        g1.add_button("\U0001f4e6 Compress", lambda: None)

        _add_separator(panel)

        g2 = RibbonGroup(panel, "Advanced")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\U0001f517 Flatten", lambda: None)
        g2.add_button("\U0001f510 Password", lambda: None)
        g2.add_button("\U0001f4dd Form Edit", lambda: None)

    def _build_help_tab(panel):
        g1 = RibbonGroup(panel, "Help")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\u2139 About", editor.show_about)
        g1.add_button("\u2328 Shortcuts", lambda: None)
        g1.add_button("\U0001f504 Updates", lambda: None)

    _build_file_tab(tabs["File"])
    _build_home_tab(tabs["Home"])
    _build_insert_tab(tabs["Insert"])
    _build_annotate_tab(tabs["Annotate"])
    _build_page_tab(tabs["Page"])
    _build_view_tab(tabs["View"])
    _build_tools_tab(tabs["Tools"])
    _build_help_tab(tabs["Help"])

    editor._ribbon_tab_buttons = tab_buttons
    editor._ribbon_tabs = tabs

    switch_tab("Home")

    return ribbon_frame


def update_ribbon_state(editor):
    has_doc = editor.current_pdf is not None
    has_elem = editor.selected_element is not None
    has_page = editor.total_pages > 0

    for tab_name, panel in getattr(editor, "_ribbon_tabs", {}).items():
        for child in panel.winfo_children():
            if isinstance(child, RibbonGroup):
                for btn in child.btn_frame.winfo_children():
                    if isinstance(btn, tk.Button):
                        pass
