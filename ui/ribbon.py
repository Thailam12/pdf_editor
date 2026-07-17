import tkinter as tk
from tkinter import ttk, colorchooser, messagebox

try:
    import customtkinter as ctk
except Exception:
    ctk = None


class Theme:
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
    DISABLED_FG = "#585b70"
    TOOLTIP_BG = "#313244"
    TOOLTIP_FG = "#cdd6f4"


BG = Theme.BG
FG = Theme.FG
ACCENT = Theme.ACCENT
BTN_BG = Theme.BTN_BG
BTN_FG = Theme.BTN_FG
ACTIVE_BG = Theme.ACTIVE_BG
HOVER_BG = Theme.HOVER_BG
TAB_BG = Theme.TAB_BG
SEPARATOR_BG = Theme.SEPARATOR_BG
DROPDOWN_BG = Theme.DROPDOWN_BG

BTN_W = 70
BTN_H = 55
ICON_AREA_H = 20

_all_ribbon_buttons = []
_all_ribbon_labels = []
_all_ribbon_combos = []
_all_ribbon_frames = []


def _make_ribbon_button(parent, icon_text, label, command=None, tooltip="", **kw):
    frame = tk.Frame(
        parent,
        bg=kw.pop("bg", BTN_BG),
        width=BTN_W,
        height=BTN_H,
    )
    frame.pack_propagate(False)

    icon_lbl = tk.Label(
        frame,
        text=icon_text,
        bg=frame["bg"],
        fg=kw.pop("fg", BTN_FG),
        font=("Segoe UI", 12),
        anchor="center",
    )
    icon_lbl.pack(side=tk.TOP, fill=tk.X, expand=True, pady=(3, 0))

    text_lbl = tk.Label(
        frame,
        text=label,
        bg=frame["bg"],
        fg=kw.pop("label_fg", BTN_FG),
        font=("Segoe UI", 7),
        anchor="center",
        wraplength=BTN_W - 4,
    )
    text_lbl.pack(side=tk.TOP, fill=tk.X, pady=(0, 2))

    if command:
        def _on_click(e, c=command):
            if frame["state"] != "disabled":
                c()

        frame.bind("<Button-1>", _on_click)
        icon_lbl.bind("<Button-1>", _on_click)
        text_lbl.bind("<Button-1>", _on_click)

    def _on_enter(e):
        if frame["state"] != "disabled":
            frame.configure(bg=HOVER_BG)
            icon_lbl.configure(bg=HOVER_BG)
            text_lbl.configure(bg=HOVER_BG)

    def _on_leave(e):
        if frame["state"] != "disabled":
            cur_bg = BTN_BG
            frame.configure(bg=cur_bg)
            icon_lbl.configure(bg=cur_bg)
            text_lbl.configure(bg=cur_bg)

    for w in (frame, icon_lbl, text_lbl):
        w.bind("<Enter>", _on_enter)
        w.bind("<Leave>", _on_leave)

    frame._icon_label = icon_lbl
    frame._text_label = text_lbl
    frame._tooltip_text = tooltip

    if tooltip:
        _add_tooltip(frame, tooltip)
        _add_tooltip(icon_lbl, tooltip)
        _add_tooltip(text_lbl, tooltip)

    _all_ribbon_buttons.append(frame)
    return frame


def _make_mini_button(parent, icon_text, label, command=None, tooltip="", **kw):
    frame = tk.Frame(
        parent,
        bg=kw.pop("bg", BTN_BG),
        width=BTN_W,
        height=30,
    )
    frame.pack_propagate(False)

    icon_lbl = tk.Label(
        frame,
        text=icon_text,
        bg=frame["bg"],
        fg=kw.pop("fg", BTN_FG),
        font=("Segoe UI", 9),
        width=3,
        anchor="center",
    )
    icon_lbl.pack(side=tk.LEFT, padx=(3, 0))

    text_lbl = tk.Label(
        frame,
        text=label,
        bg=frame["bg"],
        fg=kw.pop("label_fg", BTN_FG),
        font=("Segoe UI", 8),
        anchor="w",
    )
    text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 4))

    if command:
        def _on_click(e, c=command):
            if frame["state"] != "disabled":
                c()

        frame.bind("<Button-1>", _on_click)
        icon_lbl.bind("<Button-1>", _on_click)
        text_lbl.bind("<Button-1>", _on_click)

    def _on_enter(e):
        if frame["state"] != "disabled":
            frame.configure(bg=HOVER_BG)
            icon_lbl.configure(bg=HOVER_BG)
            text_lbl.configure(bg=HOVER_BG)

    def _on_leave(e):
        if frame["state"] != "disabled":
            frame.configure(bg=BTN_BG)
            icon_lbl.configure(bg=BTN_BG)
            text_lbl.configure(bg=BTN_BG)

    for w in (frame, icon_lbl, text_lbl):
        w.bind("<Enter>", _on_enter)
        w.bind("<Leave>", _on_leave)

    frame._icon_label = icon_lbl
    frame._text_label = text_lbl
    frame._tooltip_text = tooltip

    if tooltip:
        _add_tooltip(frame, tooltip)
        _add_tooltip(icon_lbl, tooltip)
        _add_tooltip(text_lbl, tooltip)

    _all_ribbon_buttons.append(frame)
    return frame


class _Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self._delay_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._cancel, add="+")
        widget.bind("<ButtonPress>", self._cancel, add="+")

    def _schedule(self, event=None):
        self._cancel()
        self._delay_id = self.widget.after(700, self._show)

    def _show(self):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        try:
            tw.wm_attributes("-topmost", True)
        except Exception:
            pass
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background=Theme.TOOLTIP_BG,
            foreground=Theme.TOOLTIP_FG,
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 8),
            padx=6,
            pady=3,
        )
        label.pack()

    def _cancel(self, event=None):
        if self._delay_id:
            self.widget.after_cancel(self._delay_id)
            self._delay_id = None
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


def _add_tooltip(widget, text):
    _Tooltip(widget, text)


class RibbonGroup(tk.Frame):
    def __init__(self, parent, label, **kw):
        super().__init__(parent, bg=Theme.BG, **kw)
        self._label_text = label
        self.btn_frame = tk.Frame(self, bg=Theme.BG)
        self.btn_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=1)
        self.bottom_label = tk.Label(
            self,
            text=label,
            bg=Theme.BG,
            fg="#a6adc8",
            font=("Segoe UI", 7),
            anchor="center",
        )
        self.bottom_label.pack(side=tk.BOTTOM, fill=tk.X)
        _all_ribbon_labels.append(self.bottom_label)
        _all_ribbon_frames.append(self)

    def add_button(self, icon_text, label, command=None, tooltip="", **kw):
        btn = _make_ribbon_button(
            self.btn_frame, icon_text, label, command, tooltip, **kw
        )
        btn.pack(
            side=kw.pop("side", tk.LEFT), padx=1, pady=1, anchor="n"
        )
        return btn

    def add_mini_button(self, icon_text, label, command=None, tooltip="", **kw):
        btn = _make_mini_button(
            self.btn_frame, icon_text, label, command, tooltip, **kw
        )
        btn.pack(
            side=kw.pop("side", tk.TOP), padx=1, pady=1, anchor="w", fill=tk.X
        )
        return btn

    def add_button_grid(self, icon_text, label, command=None, tooltip="", row=0, col=0, **kw):
        btn = _make_ribbon_button(
            self.btn_frame, icon_text, label, command, tooltip, **kw
        )
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
            bg=Theme.DROPDOWN_BG,
            fg=Theme.FG,
            activebackground=Theme.ACCENT,
            activeforeground=Theme.BG,
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
    def __init__(self, parent, label, icon_text, items, tooltip="", **kw):
        super().__init__(parent, bg=Theme.BG, **kw)
        self.btn = tk.Button(
            self,
            text=f"{icon_text} {label} \u25be",
            bg=Theme.BTN_BG,
            fg=Theme.BTN_FG,
            activebackground=Theme.ACTIVE_BG,
            activeforeground=Theme.FG,
            relief="flat",
            bd=0,
            font=("Segoe UI", 8),
            cursor="hand2",
            padx=4,
            pady=2,
            width=10,
        )
        self.btn.pack(side=tk.LEFT)
        self.btn.bind("<Enter>", lambda e: self.btn.configure(bg=Theme.HOVER_BG))
        self.btn.bind("<Leave>", lambda e: self.btn.configure(bg=Theme.BTN_BG))
        self._dropdown = _DropdownMenu(self.btn, items, None)
        self._menu = None
        if tooltip:
            _add_tooltip(self.btn, tooltip)
        _all_ribbon_buttons.append(self)

    def set_command(self, command):
        self._dropdown._show = lambda: self._show_menu(command)

    def _show_menu(self, command):
        if self._menu is not None:
            self._menu.destroy()
        self._menu = tk.Menu(
            self.btn,
            tearoff=0,
            bg=Theme.DROPDOWN_BG,
            fg=Theme.FG,
            activebackground=Theme.ACCENT,
            activeforeground=Theme.BG,
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
    sep = tk.Frame(parent, bg=Theme.SEPARATOR_BG, width=2)
    sep.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)
    _all_ribbon_frames.append(sep)
    return sep


def create_ribbon(editor, parent):
    ribbon_frame = tk.Frame(parent, bg=Theme.BG, bd=0, highlightthickness=0)
    ribbon_frame.pack(side=tk.TOP, fill=tk.X)
    _all_ribbon_frames.append(ribbon_frame)

    tab_bar = tk.Frame(ribbon_frame, bg=Theme.BG, bd=0)
    tab_bar.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4, 0))
    _all_ribbon_frames.append(tab_bar)

    panels_container = tk.Frame(ribbon_frame, bg=Theme.BG, bd=0)
    panels_container.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(0, 2))
    _all_ribbon_frames.append(panels_container)

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
                btn.configure(bg=Theme.ACCENT, fg=Theme.BG)
            else:
                btn.configure(bg=Theme.BG, fg=Theme.FG)

    tab_names = ["File", "Home", "Insert", "Annotate", "Page", "View", "Tools", "Help"]
    for tname in tab_names:
        panel = tk.Frame(panels_container, bg=Theme.BG, bd=0)
        tabs[tname] = panel

        btn = tk.Button(
            tab_bar,
            text=tname,
            command=lambda n=tname: switch_tab(n),
            bg=Theme.BG,
            fg=Theme.FG,
            activebackground=Theme.ACTIVE_BG,
            activeforeground=Theme.FG,
            relief="flat",
            bd=0,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            cursor="hand2",
        )
        btn.pack(side=tk.LEFT, padx=1)

        def _enter(e, b=btn):
            if active_tab.get() != b.cget("text"):
                b.configure(bg=Theme.ACTIVE_BG)

        def _leave(e, b=btn):
            if active_tab.get() != b.cget("text"):
                b.configure(bg=Theme.BG)

        btn.bind("<Enter>", _enter)
        btn.bind("<Leave>", _leave)
        tab_buttons[tname] = btn
        _all_ribbon_buttons.append(btn)

    def _build_file_tab(panel):
        g = RibbonGroup(panel, "File")
        g.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g.add_button("\U0001f4c4", "New", editor.new_document, "Create a new blank document")
        g.add_button("\U0001f4c2", "Open", editor.open_pdf, "Open an existing PDF file")
        g.add_button("\U0001f4be", "Save", editor.save_pdf, "Save the current document")
        g.add_button("\U0001f4cb", "Save As", editor.save_as_pdf, "Save the document with a new name")
        _add_separator(panel)
        g2 = RibbonGroup(panel, "Output")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\U0001f5a8", "Print", editor.print_pdf, "Print the current document")
        g2.add_button("\U0001f4e4", "Export", editor.export_images, "Export to other formats")
        _add_separator(panel)
        g3 = RibbonGroup(panel, "Close")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\U0001f512", "Close", editor.root.quit, "Close the application")

    def _build_home_tab(panel):
        # --- Clipboard ---
        g1 = RibbonGroup(panel, "Clipboard")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\u2702", "Cut", lambda: editor.root.event_generate("<<Cut>>"), "Cut selected content to clipboard")
        g1.add_button("\U0001f4cb", "Copy", lambda: editor.root.event_generate("<<Copy>>"), "Copy selected content to clipboard")
        g1.add_button("\U0001f4ea", "Paste", lambda: editor.root.event_generate("<<Paste>>"), "Paste content from clipboard")
        paste_special = RibbonDropdown(
            g1.btn_frame, "Paste Sp.", "\U0001f4ea",
            [
                ("Paste in Place", lambda: None),
                ("Paste as Text", lambda: None),
            ],
            "Paste special options",
        )
        paste_special.pack(side=tk.LEFT, padx=1, pady=1)

        _add_separator(panel)

        # --- Undo ---
        g2 = RibbonGroup(panel, "Undo")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\u21b6", "Undo", editor.undo, "Undo the last action")
        g2.add_button("\u21b7", "Redo", editor.redo, "Redo the last undone action")

        _add_separator(panel)

        # --- Tools ---
        g3 = RibbonGroup(panel, "Tools")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\U0001f5c1", "Select", lambda: editor.set_tool("select"), "Switch to selection mode")
        g3.add_button("\U0001f520", "Text", editor.add_text_element, "Insert a text element")
        g3.add_button("\U0001f5bc", "Image", editor.add_image_tool if hasattr(editor, 'add_image_tool') else editor.add_image_element if hasattr(editor, 'add_image_element') else lambda: None, "Insert an image element")
        shape_items = [
            ("\u25a1 Rectangle", lambda: editor.start_drawing("rect")),
            ("\u25cb Ellipse", lambda: editor.start_drawing("ellipse")),
            ("\u25b3 Triangle", lambda: editor.start_drawing("triangle")),
            ("\u2571 Line", lambda: editor.start_drawing("line")),
            ("\u2192 Arrow", lambda: editor.start_drawing("arrow")),
            ("---", None),
            ("\u2b21 Polygon", lambda: editor.start_drawing("polygon")),
            ("\u2726 Star", lambda: editor.start_drawing("star")),
        ]
        shape_btn_frame = _make_ribbon_button(g3.btn_frame, "\u2b21", "Shape \u25be", None, "Insert a shape element")
        shape_btn_frame.pack(side=tk.LEFT, padx=1, pady=1, anchor="n")
        shape_menu = _DropdownMenu(shape_btn_frame, shape_items, None)
        _add_separator(panel)

        g3b = RibbonGroup(panel, "Draw")
        g3b.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3b.add_button("\u270d", "Freehand", lambda: editor.start_drawing("freehand"), "Draw freehand on the page")

        _add_separator(panel)

        # --- Font ---
        g4 = RibbonGroup(panel, "Font")
        g4.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g4.btn_frame.columnconfigure(0, weight=1)
        g4.btn_frame.columnconfigure(1, weight=0)

        font_frame = tk.Frame(g4.btn_frame, bg=Theme.BG)
        font_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=1, pady=1)
        tk.Label(font_frame, text="Font:", bg=Theme.BG, fg=Theme.FG, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)
        font_var = tk.StringVar(value="Arial")
        font_combo = ttk.Combobox(
            font_frame, textvariable=font_var,
            values=["Arial", "Times New Roman", "Courier New", "Calibri", "Verdana", "Helvetica", "Georgia", "Trebuchet MS", "Comic Sans MS", "Impact"],
            width=14, state="readonly",
        )
        font_combo.pack(side=tk.LEFT, padx=2)
        font_combo.bind("<<ComboboxSelected>>", lambda e: editor.set_font(font_var.get()))
        editor.font_var = font_var
        _all_ribbon_combos.append(font_combo)

        size_frame = tk.Frame(g4.btn_frame, bg=Theme.BG)
        size_frame.grid(row=0, column=1, sticky="ew", padx=1, pady=1)
        tk.Label(size_frame, text="Sz:", bg=Theme.BG, fg=Theme.FG, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=1)
        size_var = tk.IntVar(value=12)
        size_combo = ttk.Combobox(
            size_frame, textvariable=size_var,
            values=[6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 48, 60, 72, 96],
            width=4, state="readonly",
        )
        size_combo.pack(side=tk.LEFT, padx=1)
        size_combo.bind("<<ComboboxSelected>>", lambda e: editor.set_font_size(size_var.get()))
        editor.size_var = size_var
        _all_ribbon_combos.append(size_combo)

        style_frame = tk.Frame(g4.btn_frame, bg=Theme.BG)
        style_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=1, pady=1)

        bold_btn = tk.Button(
            style_frame, text="B", command=editor.toggle_bold,
            bg=Theme.BTN_BG, fg=Theme.BTN_FG, font=("Segoe UI", 9, "bold"),
            width=3, relief="flat", bd=0, cursor="hand2",
        )
        bold_btn.pack(side=tk.LEFT, padx=1)
        editor.bold_btn = bold_btn
        _add_tooltip(bold_btn, "Toggle bold formatting")
        _all_ribbon_buttons.append(bold_btn)

        italic_btn = tk.Button(
            style_frame, text="I", command=editor.toggle_italic,
            bg=Theme.BTN_BG, fg=Theme.BTN_FG, font=("Segoe UI", 9, "italic"),
            width=3, relief="flat", bd=0, cursor="hand2",
        )
        italic_btn.pack(side=tk.LEFT, padx=1)
        editor.italic_btn = italic_btn
        _add_tooltip(italic_btn, "Toggle italic formatting")
        _all_ribbon_buttons.append(italic_btn)

        underline_btn = tk.Button(
            style_frame, text="U", command=editor.toggle_underline,
            bg=Theme.BTN_BG, fg=Theme.BTN_FG, font=("Segoe UI", 9, "underline"),
            width=3, relief="flat", bd=0, cursor="hand2",
        )
        underline_btn.pack(side=tk.LEFT, padx=1)
        editor.underline_btn = underline_btn
        _add_tooltip(underline_btn, "Toggle underline formatting")
        _all_ribbon_buttons.append(underline_btn)

        strike_frame = tk.Frame(g4.btn_frame, bg=Theme.BG)
        strike_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=1, pady=1)

        strike_btn = tk.Button(
            strike_frame, text="S",
            command=getattr(editor, "toggle_strikethrough", lambda: None),
            bg=Theme.BTN_BG, fg=Theme.BTN_FG,
            font=("Segoe UI", 9, "overstrike"),
            width=3, relief="flat", bd=0, cursor="hand2",
        )
        strike_btn.pack(side=tk.LEFT, padx=1)
        _add_tooltip(strike_btn, "Toggle strikethrough formatting")
        _all_ribbon_buttons.append(strike_btn)

        def _pick_color():
            try:
                color = colorchooser.askcolor(initialcolor="#000000", title="Font Color")
                if color and color[1]:
                    if hasattr(editor, "set_font_color"):
                        editor.set_font_color(color[1])
            except Exception:
                pass

        color_btn = tk.Button(
            strike_frame, text="\u2588",
            command=_pick_color,
            bg=Theme.BTN_BG, fg="#ff0000",
            font=("Segoe UI", 9),
            width=3, relief="flat", bd=0, cursor="hand2",
        )
        color_btn.pack(side=tk.LEFT, padx=1)
        _add_tooltip(color_btn, "Pick font color")
        _all_ribbon_buttons.append(color_btn)

        _add_separator(panel)

        # --- Paragraph ---
        g5 = RibbonGroup(panel, "Paragraph")
        g5.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g5.add_button("\u258f", "Left", lambda: editor.set_alignment("left"), "Align text to the left")
        g5.add_button("\u2585", "Center", lambda: editor.set_alignment("center"), "Center align text")
        g5.add_button("\u258e", "Right", lambda: editor.set_alignment("right"), "Align text to the right")
        g5.add_button("\u2587", "Justify", lambda: editor.set_alignment("justify"), "Justify text alignment")

        spacing_items = [
            ("1.0  Single", lambda: editor.set_line_spacing(1.0) if hasattr(editor, "set_line_spacing") else None),
            ("1.15", lambda: editor.set_line_spacing(1.15) if hasattr(editor, "set_line_spacing") else None),
            ("1.5", lambda: editor.set_line_spacing(1.5) if hasattr(editor, "set_line_spacing") else None),
            ("2.0  Double", lambda: editor.set_line_spacing(2.0) if hasattr(editor, "set_line_spacing") else None),
            ("2.5", lambda: editor.set_line_spacing(2.5) if hasattr(editor, "set_line_spacing") else None),
            ("3.0  Triple", lambda: editor.set_line_spacing(3.0) if hasattr(editor, "set_line_spacing") else None),
        ]
        RibbonDropdown(g5.btn_frame, "Spacing", "\u21f5", spacing_items, "Set line spacing").pack(side=tk.LEFT, padx=1, pady=1)

        _add_separator(panel)

        # --- Edit ---
        g6 = RibbonGroup(panel, "Edit")
        g6.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g6.add_button("\u2716", "Delete", editor.delete_selected_element, "Delete the selected element")
        g6.add_button("\u2714", "Select All", getattr(editor, "select_all", lambda: None), "Select all elements on the page")
        g6.add_button("\U0001f50d", "Find", getattr(editor, "find_replace", lambda: None), "Find and replace text in the document")

    def _build_insert_tab(panel):
        # --- Text ---
        g1 = RibbonGroup(panel, "Text")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\U0001f524", "Text", editor.add_text_element, "Insert a text element on the page")
        g1.add_button("\U0001f4dd", "Text Box", getattr(editor, "_add_textbox", lambda: None), "Insert a text box element")
        g1.add_button("\U0001f4ac", "Callout", getattr(editor, "_add_callout", lambda: None), "Insert a callout / speech bubble")

        _add_separator(panel)

        # --- Images ---
        g2 = RibbonGroup(panel, "Images")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\U0001f5bc", "Image", editor.add_image_tool if hasattr(editor, 'add_image_tool') else lambda: None, "Insert an image from file")
        barcode_items = [
            ("QR Code", lambda: editor.generate_barcode("qr") if hasattr(editor, "generate_barcode") else None),
            ("Code 128", lambda: editor.generate_barcode("code128") if hasattr(editor, "generate_barcode") else None),
            ("Code 39", lambda: editor.generate_barcode("code39") if hasattr(editor, "generate_barcode") else None),
            ("EAN-13", lambda: editor.generate_barcode("ean13") if hasattr(editor, "generate_barcode") else None),
        ]
        RibbonDropdown(g2.btn_frame, "Barcode", "\u2022", barcode_items, "Generate and insert a barcode").pack(side=tk.LEFT, padx=1, pady=1)

        _add_separator(panel)

        # --- Annotations ---
        g3 = RibbonGroup(panel, "Annotations")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\U0001f4ac", "Stamp", getattr(editor, "add_stamp", lambda: None), "Place a stamp on the page")
        g3.add_button("\u270d", "Signature", getattr(editor, "add_signature", lambda: None), "Insert a digital signature")
        g3.add_button("\U0001f517", "Link", getattr(editor, "add_link", lambda: None), "Insert a hyperlink")
        g3.add_button("\U0001f4dd", "Note", getattr(editor, "add_note", lambda: None), "Add a sticky note annotation")

        _add_separator(panel)

        # --- Media ---
        g4 = RibbonGroup(panel, "Media")
        g4.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g4.add_button("\U0001f3ac", "Video", getattr(editor, "insert_video", lambda: None), "Embed a video file")
        g4.add_button("\U0001f3b5", "Audio", getattr(editor, "insert_audio", lambda: None), "Embed an audio file")

        _add_separator(panel)

        # --- Document ---
        g5 = RibbonGroup(panel, "Document")
        g5.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g5.add_button("\u2602", "Watermark", getattr(editor, "add_watermark", lambda: None), "Add a watermark to pages")
        g5.add_button("\U0001f4dd", "Header/Footer", getattr(editor, "add_header_footer", lambda: None), "Add header and footer to pages")
        g5.add_button("\U0001f4c4", "Page No.", getattr(editor, "add_page_numbers", lambda: None), "Add page numbers to the document")
        g5.add_button("\U0001f58c", "Background", getattr(editor, "set_background", lambda: None), "Set page background color or image")

        _add_separator(panel)

        # --- Forms ---
        g6 = RibbonGroup(panel, "Forms")
        g6.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g6.add_button("\u2b1c", "Text Field", getattr(editor, "add_form_textfield", lambda: None), "Insert a form text field")
        g6.add_button("\u2611", "Checkbox", getattr(editor, "add_form_checkbox", lambda: None), "Insert a form checkbox")
        g6.add_button("\u25bc", "Dropdown", getattr(editor, "add_form_dropdown", lambda: None), "Insert a form dropdown")
        g6.add_button("\u270d", "Sig. Field", getattr(editor, "add_form_signature_field", lambda: None), "Insert a signature form field")

        _add_separator(panel)

        # --- Attachments ---
        g7 = RibbonGroup(panel, "Attachments")
        g7.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g7.add_button("\U0001f4ce", "File", getattr(editor, "attach_file", lambda: None), "Attach an external file to the PDF")

    def _build_annotate_tab(panel):
        # --- Markup ---
        g1 = RibbonGroup(panel, "Markup")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\U0001f4dd", "Highlight", lambda: editor.start_drawing("highlight"), "Highlight selected text")
        g1.add_button("\u0332", "Underline", getattr(editor, "underline_annot", lambda: None), "Underline selected text")
        g1.add_button("\u0336", "Strike", getattr(editor, "strikethrough_annot", lambda: None), "Strikethrough selected text")
        g1.add_button("\u2581", "Squiggly", getattr(editor, "squiggly_annot", lambda: None), "Add squiggly underline")

        _add_separator(panel)

        # --- Drawing ---
        g2 = RibbonGroup(panel, "Drawing")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\u270d", "Freehand", lambda: editor.start_drawing("freehand"), "Draw freehand annotations")
        g2.add_button("\U0001f9f9", "Eraser", getattr(editor, "activate_eraser", lambda: None), "Erase freehand drawings")

        _add_separator(panel)

        # --- Notes ---
        g3 = RibbonGroup(panel, "Notes")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\U0001f4ad", "Sticky", getattr(editor, "add_sticky_note", lambda: None), "Add a sticky note")
        g3.add_button("\U0001f520", "Text Box", editor.add_text_element, "Add a text box annotation")
        g3.add_button("\U0001f4ac", "Callout", getattr(editor, "add_callout", lambda: None), "Add a callout annotation")

        _add_separator(panel)

        # --- Stamps ---
        g4 = RibbonGroup(panel, "Stamps")
        g4.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        stamp_items = [
            ("Approved", lambda: editor.apply_stamp("approved") if hasattr(editor, "apply_stamp") else None),
            ("Rejected", lambda: editor.apply_stamp("rejected") if hasattr(editor, "apply_stamp") else None),
            ("Draft", lambda: editor.apply_stamp("draft") if hasattr(editor, "apply_stamp") else None),
            ("Final", lambda: editor.apply_stamp("final") if hasattr(editor, "apply_stamp") else None),
            ("Confidential", lambda: editor.apply_stamp("confidential") if hasattr(editor, "apply_stamp") else None),
            ("---", None),
            ("Paid", lambda: editor.apply_stamp("paid") if hasattr(editor, "apply_stamp") else None),
            ("Void", lambda: editor.apply_stamp("void") if hasattr(editor, "apply_stamp") else None),
        ]
        RibbonDropdown(g4.btn_frame, "Stamps", "\U0001f4ac", stamp_items, "Insert a predefined stamp").pack(side=tk.LEFT, padx=1, pady=1)
        g4.add_button("\u2795", "Custom", getattr(editor, "create_custom_stamp", lambda: None), "Create a custom stamp")
        g4.add_button("\U0001f4c5", "Date", getattr(editor, "add_date_stamp", lambda: None), "Insert a date stamp")

        _add_separator(panel)

        # --- Redact ---
        g5 = RibbonGroup(panel, "Redact")
        g5.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g5.add_button("\u2b1b", "Mark", getattr(editor, "mark_redaction", lambda: None), "Mark areas for redaction")
        g5.add_button("\u2714", "Apply", getattr(editor, "apply_redactions", lambda: None), "Apply all marked redactions permanently")
        g5.add_button("\u2716", "Clear", getattr(editor, "clear_redactions", lambda: None), "Clear all redaction marks")

        _add_separator(panel)

        # --- Measurement ---
        g6 = RibbonGroup(panel, "Measurement")
        g6.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g6.add_button("\u2194", "Distance", getattr(editor, "measure_distance", lambda: None), "Measure distance between two points")
        g6.add_button("\u25ad", "Perimeter", getattr(editor, "measure_perimeter", lambda: None), "Measure perimeter of a region")
        g6.add_button("\u25a1", "Area", getattr(editor, "measure_area", lambda: None), "Measure area of a region")

    def _build_page_tab(panel):
        # --- Manage ---
        g1 = RibbonGroup(panel, "Manage")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\u2795", "Insert", getattr(editor, "insert_page", lambda: None), "Insert a new blank page")
        g1.add_button("\u2796", "Delete", getattr(editor, "delete_page", lambda: None), "Delete the current page")
        g1.add_button("\u2398", "Duplicate", getattr(editor, "duplicate_page", lambda: None), "Duplicate the current page")
        g1.add_button("\u2b06", "Move", getattr(editor, "move_page", lambda: None), "Move a page to a different position")

        _add_separator(panel)

        # --- Transform ---
        g2 = RibbonGroup(panel, "Transform")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\U0001f504", "Rotate CW", getattr(editor, "rotate_page_cw", lambda: None), "Rotate page 90\u00b0 clockwise")
        g2.add_button("\U0001f504", "Rotate CCW", getattr(editor, "rotate_page_ccw", lambda: None), "Rotate page 90\u00b0 counter-clockwise")
        g2.add_button("\u2702", "Crop", getattr(editor, "crop_page", lambda: None), "Crop the current page")
        g2.add_button("\u21f5", "Resize", getattr(editor, "resize_page", lambda: None), "Resize the current page")

        _add_separator(panel)

        # --- Organize ---
        g3 = RibbonGroup(panel, "Organize")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\U0001f4d5", "Merge", getattr(editor, "merge_pdfs", lambda: None), "Merge multiple PDF files")
        g3.add_button("\u2702", "Split", getattr(editor, "split_pdf", lambda: None), "Split the PDF into multiple files")
        g3.add_button("\U0001f4e5", "Extract", getattr(editor, "extract_pages", lambda: None), "Extract selected pages to a new file")

        _add_separator(panel)

        # --- Background ---
        g4 = RibbonGroup(panel, "Background")
        g4.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g4.add_button("\U0001f7e2", "Color", getattr(editor, "set_bg_color", lambda: None), "Set page background color")
        g4.add_button("\U0001f5bc", "Image", getattr(editor, "set_bg_image", lambda: None), "Set page background image")
        g4.add_button("\u2716", "Remove", getattr(editor, "remove_background", lambda: None), "Remove page background")

        _add_separator(panel)

        # --- Bates ---
        g5 = RibbonGroup(panel, "Bates")
        g5.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g5.add_button("\U0001f4dd", "Bates No.", getattr(editor, "add_bates_numbers", lambda: None), "Add Bates numbering to pages")

    def _build_view_tab(panel):
        # --- Zoom ---
        g1 = RibbonGroup(panel, "Zoom")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\U0001f50d", "Zoom In", lambda: editor.set_zoom(editor.zoom_level + 10), "Zoom in (+10%)")
        g1.add_button("\U0001f50e", "Zoom Out", lambda: editor.set_zoom(editor.zoom_level - 10), "Zoom out (-10%)")
        g1.add_button("\U0001f4d0", "Fit Page", lambda: editor.set_zoom(getattr(editor, "fit_page_zoom", 100)), "Fit entire page in view")
        g1.add_button("\u21f4", "Fit Width", lambda: editor.set_zoom(getattr(editor, "fit_width_zoom", 100)), "Fit page width in view")
        g1.add_button("\u21f5", "Actual", lambda: editor.set_zoom(100), "Show at 100% actual size")

        _add_separator(panel)

        # --- Layout ---
        g2 = RibbonGroup(panel, "Layout")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\u258c", "Single", getattr(editor, "set_single_page", lambda: None), "Show one page at a time")
        g2.add_button("\u2583\u2583", "Facing", getattr(editor, "set_facing_pages", lambda: None), "Show pages side by side")
        g2.add_button("\u21f5", "Cont.", getattr(editor, "set_continuous_scroll", lambda: None), "Continuous vertical scroll")
        g2.add_button("\u2b1a", "Grid", getattr(editor, "set_grid_layout", lambda: None), "Show pages in a grid layout")

        _add_separator(panel)

        # --- Navigation ---
        g3 = RibbonGroup(panel, "Navigation")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\u23ee", "Prev", getattr(editor, "prev_page", lambda: None), "Go to the previous page")
        g3.add_button("\u23ed", "Next", getattr(editor, "next_page", lambda: None), "Go to the next page")
        g3.add_button("\u23ee", "First", getattr(editor, "first_page", lambda: None), "Go to the first page")
        g3.add_button("\u23ed", "Last", getattr(editor, "last_page", lambda: None), "Go to the last page")
        g3.add_button("\U0001f4dd", "Go To", getattr(editor, "go_to_page_dialog", lambda: None), "Navigate to a specific page number")

        _add_separator(panel)

        # --- Display ---
        g4 = RibbonGroup(panel, "Display")
        g4.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g4.add_button("\u2316", "Rulers", getattr(editor, "toggle_rulers", lambda: None), "Show or hide rulers")
        g4.add_button("\u2506", "Guides", getattr(editor, "toggle_guides", lambda: None), "Show or hide alignment guides")
        g4.add_button("\u2b1a", "Grid", getattr(editor, "toggle_grid_overlay", lambda: None), "Show or hide the grid overlay")
        g4.add_button("\U0001f500", "Snap", getattr(editor, "toggle_snap", lambda: None), "Toggle snap to grid/guides")
        g4.add_button("\U0001f319", "Dark", getattr(editor, "toggle_dark_mode", lambda: None), "Toggle dark mode")

        theme_items = [
            ("Catppuccin (Default)", lambda: editor.set_theme("catppuccin") if hasattr(editor, "set_theme") else None),
            ("Dracula", lambda: editor.set_theme("dracula") if hasattr(editor, "set_theme") else None),
            ("Nord", lambda: editor.set_theme("nord") if hasattr(editor, "set_theme") else None),
            ("Solarized Dark", lambda: editor.set_theme("solarized_dark") if hasattr(editor, "set_theme") else None),
            ("Solarized Light", lambda: editor.set_theme("solarized_light") if hasattr(editor, "set_theme") else None),
            ("Gruvbox Dark", lambda: editor.set_theme("gruvbox_dark") if hasattr(editor, "set_theme") else None),
            ("Tokyo Night", lambda: editor.set_theme("tokyo_night") if hasattr(editor, "set_theme") else None),
            ("Light", lambda: editor.set_theme("light") if hasattr(editor, "set_theme") else None),
        ]
        RibbonDropdown(g4.btn_frame, "Theme", "\U0001f3a8", theme_items, "Switch color theme").pack(side=tk.LEFT, padx=1, pady=1)

    def _build_tools_tab(panel):
        # --- OCR ---
        g1 = RibbonGroup(panel, "OCR")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\U0001f4dd", "Current", editor.ocr_current_page if hasattr(editor, 'ocr_current_page') else lambda: None, "Run OCR on the current page")
        g1.add_button("\U0001f4da", "All Pages", getattr(editor, "ocr_all_pages", lambda: None), "Run OCR on all pages in the document")

        _add_separator(panel)

        # --- Security ---
        g2 = RibbonGroup(panel, "Security")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\U0001f510", "Password", getattr(editor, "set_password", lambda: None), "Set password protection on the PDF")
        g2.add_button("\U0001f4dd", "Certificate", getattr(editor, "certificate_sign", lambda: None), "Sign with a digital certificate")

        _add_separator(panel)

        # --- Compare ---
        g3 = RibbonGroup(panel, "Compare")
        g3.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g3.add_button("\U0001f50d", "Compare", getattr(editor, "compare_documents", lambda: None), "Compare two PDF documents")

        _add_separator(panel)

        # --- Compress ---
        g4 = RibbonGroup(panel, "Compress")
        g4.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g4.add_button("\U0001f4e6", "Compress", getattr(editor, "compress_pdf", lambda: None), "Compress the PDF to reduce file size")
        g4.add_button("\U0001f5bc", "Optimize", getattr(editor, "optimize_images", lambda: None), "Optimize embedded images for size")
        g4.add_button("\u21f4", "Linearize", getattr(editor, "linearize_pdf", lambda: None), "Linearize PDF for web delivery")

        _add_separator(panel)

        # --- AI ---
        g5 = RibbonGroup(panel, "AI")
        g5.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g5.add_button("\U0001f4dd", "Extract", getattr(editor, "ai_extract_text", lambda: None), "AI-powered text extraction")
        g5.add_button("\U0001f4ca", "Summarize", getattr(editor, "ai_summarize", lambda: None), "AI-powered document summarization")
        g5.add_button("\U0001f30d", "Translate", getattr(editor, "ai_translate", lambda: None), "AI-powered document translation")
        g5.add_button("\U0001f4c8", "Analyze", getattr(editor, "ai_analyze", lambda: None), "AI-powered document analysis")

        _add_separator(panel)

        # --- Accessibility ---
        g6 = RibbonGroup(panel, "Accessibility")
        g6.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g6.add_button("\u2714", "Check", getattr(editor, "check_accessibility", lambda: None), "Run accessibility compliance check")
        g6.add_button("\u26a0", "Fix", getattr(editor, "fix_accessibility", lambda: None), "Auto-fix accessibility issues")
        g6.add_button("\U0001f3f7", "Tags", getattr(editor, "add_pdf_tags", lambda: None), "Add structure tags for screen readers")

        _add_separator(panel)

        # --- Automation ---
        g7 = RibbonGroup(panel, "Automation")
        g7.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g7.add_button("\u2699", "Wizard", getattr(editor, "action_wizard", lambda: None), "Open the Action Wizard")
        g7.add_button("\U0001f4be", "Save Act.", getattr(editor, "save_action", lambda: None), "Save the current action sequence")
        g7.add_button("\U0001f4c2", "Load Act.", getattr(editor, "load_action", lambda: None), "Load a saved action sequence")

    def _build_help_tab(panel):
        # --- Info ---
        g1 = RibbonGroup(panel, "Info")
        g1.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g1.add_button("\u2139", "About", editor.show_about, "About this application")
        g1.add_button("\u2328", "Shortcuts", getattr(editor, "show_shortcuts", lambda: None), "View keyboard shortcuts")

        _add_separator(panel)

        # --- Support ---
        g2 = RibbonGroup(panel, "Support")
        g2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)
        g2.add_button("\U0001f504", "Updates", getattr(editor, "check_updates", lambda: None), "Check for application updates")
        g2.add_button("\U0001f4d6", "Docs", getattr(editor, "open_documentation", lambda: None), "Open the user documentation")

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

    def set_theme(theme_colors):
        global BG, FG, ACCENT, BTN_BG, BTN_FG, ACTIVE_BG, HOVER_BG, TAB_BG, SEPARATOR_BG, DROPDOWN_BG
        Theme.BG = theme_colors.get("bg", "#1e1e2e")
        Theme.FG = theme_colors.get("fg", "#cdd6f4")
        Theme.ACCENT = theme_colors.get("accent", "#89b4fa")
        Theme.BTN_BG = theme_colors.get("btn_bg", "#45475a")
        Theme.BTN_FG = theme_colors.get("btn_fg", "#cdd6f4")
        Theme.ACTIVE_BG = theme_colors.get("active_bg", "#585b70")
        Theme.HOVER_BG = theme_colors.get("hover_bg", "#585b70")
        Theme.TAB_BG = theme_colors.get("tab_bg", "#313244")
        Theme.SEPARATOR_BG = theme_colors.get("separator_bg", "#585b70")
        Theme.DROPDOWN_BG = theme_colors.get("dropdown_bg", "#313244")
        Theme.DISABLED_FG = theme_colors.get("disabled_fg", "#585b70")
        Theme.TOOLTIP_BG = theme_colors.get("tooltip_bg", "#313244")
        Theme.TOOLTIP_FG = theme_colors.get("tooltip_fg", "#cdd6f4")
        BG = Theme.BG
        FG = Theme.FG
        ACCENT = Theme.ACCENT
        BTN_BG = Theme.BTN_BG
        BTN_FG = Theme.BTN_FG
        ACTIVE_BG = Theme.ACTIVE_BG
        HOVER_BG = Theme.HOVER_BG
        TAB_BG = Theme.TAB_BG
        SEPARATOR_BG = Theme.SEPARATOR_BG
        DROPDOWN_BG = Theme.DROPDOWN_BG

        for f in _all_ribbon_frames:
            try:
                f.configure(bg=Theme.BG)
            except Exception:
                pass
            for child in f.winfo_children():
                try:
                    if isinstance(child, tk.Label):
                        is_bottom = getattr(child, "cget", None) and child.cget("font") == ("Segoe UI", 7)
                        if is_bottom:
                            child.configure(bg=Theme.BG, fg="#a6adc8")
                        else:
                            child.configure(bg=Theme.BG)
                    elif isinstance(child, tk.Frame):
                        child.configure(bg=Theme.BG)
                except Exception:
                    pass

        for lbl in _all_ribbon_labels:
            try:
                lbl.configure(bg=Theme.BG, fg="#a6adc8")
            except Exception:
                pass

        for btn in _all_ribbon_buttons:
            try:
                btn.configure(bg=Theme.BTN_BG, fg=Theme.BTN_FG,
                              activebackground=Theme.ACTIVE_BG, activeforeground=Theme.FG)
                if hasattr(btn, "_icon_label"):
                    btn._icon_label.configure(bg=Theme.BTN_BG, fg=Theme.BTN_FG)
                if hasattr(btn, "_text_label"):
                    btn._text_label.configure(bg=Theme.BTN_BG, fg=Theme.BTN_FG)
            except Exception:
                pass

        for combo in _all_ribbon_combos:
            try:
                style = ttk.Style()
                style.theme_use("clam")
                style.configure("TCombobox",
                                fieldbackground=Theme.BTN_BG,
                                background=Theme.BTN_BG,
                                foreground=Theme.BTN_FG,
                                selectbackground=Theme.ACCENT,
                                selectforeground=Theme.BG)
            except Exception:
                pass

        current = active_tab.get()
        for t_name, btn in tab_buttons.items():
            if t_name == current:
                btn.configure(bg=Theme.ACCENT, fg=Theme.BG)
            else:
                btn.configure(bg=Theme.BG, fg=Theme.FG)

        ribbon_frame.configure(bg=Theme.BG)
        tab_bar.configure(bg=Theme.BG)
        panels_container.configure(bg=Theme.BG)
        for t_name, panel in tabs.items():
            panel.configure(bg=Theme.BG)

    editor.set_ribbon_theme = set_theme

    return ribbon_frame


def update_ribbon_state(editor):
    has_doc = editor.current_pdf is not None
    has_elem = editor.selected_element is not None
    has_page = editor.total_pages > 0
    has_undo = getattr(editor, "undo_stack", None) and len(getattr(editor, "undo_stack", [])) > 0
    has_redo = getattr(editor, "redo_stack", None) and len(getattr(editor, "redo_stack", [])) > 0
    has_selection = has_elem

    for tab_name, panel in getattr(editor, "_ribbon_tabs", {}).items():
        for child in panel.winfo_children():
            if isinstance(child, RibbonGroup):
                for btn in child.btn_frame.winfo_children():
                    if isinstance(btn, tk.Button):
                        text = btn.cget("text")
                        state = "normal"
                        if not has_doc:
                            disabled_when_no_doc = [
                                "Print", "Export", "Close",
                                "\u2702", "\U0001f4cb", "\U0001f4ea",
                                "\u21b6", "\u21b7",
                                "\U0001f5c1", "\U0001f520", "\U0001f5bc",
                                "B", "I", "U", "S", "\u2588",
                                "\u258f", "\u2585", "\u258e", "\u2587",
                                "\u2716", "\u2714", "\U0001f50d",
                                "\u23ee", "\u23ed", "\u2316", "\u2506", "\u2b1a", "\U0001f500", "\U0001f319",
                                "\U0001f50d", "\U0001f50e", "\U0001f4d0", "\u21f4", "\u21f5",
                                "\U0001f4dd", "\U0001f4da", "\U0001f510", "\U0001f4e6", "\U0001f5bc",
                                "\U0001f4ca", "\U0001f30d", "\U0001f4c8",
                                "\u2714", "\u26a0", "\U0001f3f7",
                                "\u2699", "\U0001f4be", "\U0001f4c2",
                                "\u2795", "\u2796", "\u2398", "\u2b06",
                                "\U0001f504", "\u2702", "\u21f5",
                                "\U0001f4d5", "\u2702", "\U0001f4e5",
                                "\U0001f7e2", "\U0001f5bc", "\u2716",
                                "\U0001f4dd", "\U0001f524", "\U0001f4ac", "\U0001f4ce",
                                "\U0001f517", "\u270d", "\u2b1c", "\u2611", "\u25bc",
                                "\U0001f3ac", "\U0001f3b5", "\u2602",
                                "\U0001f58c", "\U0001f4c4",
                                "\U0001f4ad", "\U0001f504",
                                "\U0001f4c4", "\U0001f4c2", "\U0001f4be", "\U0001f4cb",
                            ]
                            if text.strip() in disabled_when_no_doc:
                                state = "disabled"
                        if not has_elem:
                            if text.strip() in ["\u2716"]:
                                state = "disabled"
                        try:
                            btn.configure(state=state)
                            if state == "disabled":
                                btn.configure(fg=Theme.DISABLED_FG)
                            else:
                                btn.configure(fg=Theme.BTN_FG)
                        except Exception:
                            pass
                    elif isinstance(btn, tk.Frame):
                        try:
                            if not has_doc:
                                btn.configure(bg=Theme.DISABLED_FG)
                                if hasattr(btn, "_icon_label"):
                                    btn._icon_label.configure(fg=Theme.DISABLED_FG)
                                if hasattr(btn, "_text_label"):
                                    btn._text_label.configure(fg=Theme.DISABLED_FG)
                            else:
                                btn.configure(bg=Theme.BTN_BG)
                                if hasattr(btn, "_icon_label"):
                                    btn._icon_label.configure(fg=Theme.BTN_FG)
                                if hasattr(btn, "_text_label"):
                                    btn._text_label.configure(fg=Theme.BTN_FG)
                        except Exception:
                            pass
