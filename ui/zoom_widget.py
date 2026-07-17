import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except Exception:
    ctk = None

from ui.theme_manager import ThemeManager


ZOOM_PRESETS = [25, 50, 75, 100, 125, 150, 200, 300, 400]


class ZoomWidget:
    def __init__(self, editor):
        self.editor = editor
        self.theme = ThemeManager
        self._frame = None
        self._zoom_var = None
        self._slider = None
        self._updating = False

    def create_widget(self, parent):
        theme = self.theme
        self._frame = tk.Frame(parent, bg=theme.get_color("panel", "bg"), bd=0)
        self._frame.pack(side=tk.LEFT, padx=4)

        def _btn(text, command, width=2):
            b = tk.Button(self._frame, text=text,
                          bg=theme.get_color("button_bg", ""),
                          fg=theme.get_color("button_fg", ""),
                          font=("Segoe UI", 9),
                          relief="flat", bd=0, width=width,
                          padx=2, pady=1, cursor="hand2",
                          command=command)
            b.bind("<Enter>",
                   lambda e: b.configure(bg=theme.get_color("hover_bg", ""))
                   if b["state"] != "disabled" else None)
            b.bind("<Leave>",
                   lambda e: b.configure(bg=theme.get_color("button_bg", ""))
                   if b["state"] != "disabled" else None)
            return b

        zoom_out_btn = _btn("\u2212", self._zoom_out, 2)
        zoom_out_btn.pack(side=tk.LEFT, padx=1)

        self._zoom_var = tk.StringVar(value=f"{self.editor.zoom_level}%")
        self._zoom_entry = tk.Entry(self._frame, textvariable=self._zoom_var,
                                    width=5,
                                    bg=theme.get_color("entry_bg", ""),
                                    fg=theme.get_color("text", "primary"),
                                    insertbackground=theme.get_color("text", "primary"),
                                    font=("Segoe UI", 9),
                                    relief="flat", bd=0,
                                    justify="center",
                                    highlightthickness=1,
                                    highlightbackground=theme.get_color("surface", "border"),
                                    highlightcolor=theme.get_color("accent", "bg"))
        self._zoom_entry.pack(side=tk.LEFT, padx=2, ipady=1)
        self._zoom_entry.bind("<Return>", self._on_entry_return)
        self._zoom_entry.bind("<FocusOut>", self._on_entry_return)

        zoom_in_btn = _btn("+", self._zoom_in, 2)
        zoom_in_btn.pack(side=tk.LEFT, padx=1)

        sep = tk.Frame(self._frame, bg=theme.get_color("separator", ""), width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)

        self._preset_var = tk.StringVar(value="100%")
        preset_values = [f"{p}%" for p in ZOOM_PRESETS]
        preset_menu = tk.OptionMenu(self._frame, self._preset_var, *preset_values,
                                    command=self._on_preset_select)
        preset_menu.configure(bg=theme.get_color("button_bg", ""),
                              fg=theme.get_color("button_fg", ""),
                              activebackground=theme.get_color("hover_bg", ""),
                              activeforeground=theme.get_color("button_fg", ""),
                              font=("Segoe UI", 8),
                              highlightthickness=0, bd=0,
                              relief="flat", indicatoron=False,
                              padx=4, pady=1)
        preset_menu["menu"].configure(bg=theme.get_color("menu_bg", ""),
                                      fg=theme.get_color("text", "primary"),
                                      activebackground=theme.get_color("accent", "bg"),
                                      activeforeground=theme.get_color("bg", ""),
                                      font=("Segoe UI", 8))
        preset_menu.pack(side=tk.LEFT, padx=2)

        sep2 = tk.Frame(self._frame, bg=theme.get_color("separator", ""), width=1)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)

        fit_page_btn = _btn("\u25a1", self._fit_page, 3)
        fit_page_btn.pack(side=tk.LEFT, padx=1)
        self._tooltip(fit_page_btn, "Fit to Page (Ctrl+0)")

        fit_width_btn = _btn("\u21f4", self._fit_width, 3)
        fit_width_btn.pack(side=tk.LEFT, padx=1)
        self._tooltip(fit_width_btn, "Fit to Width")

        actual_btn = _btn("1:1", self._actual_size, 3)
        actual_btn.pack(side=tk.LEFT, padx=1)
        self._tooltip(actual_btn, "Actual Size (Ctrl+1)")

        self._slider = tk.Scale(self._frame, from_=25, to=400,
                                orient=tk.HORIZONTAL,
                                variable=tk.IntVar(value=self.editor.zoom_level),
                                bg=theme.get_color("panel", "bg"),
                                fg=theme.get_color("text", "secondary"),
                                troughcolor=theme.get_color("surface", "bg"),
                                highlightthickness=0, bd=0,
                                sliderlength=12, showvalue=False,
                                length=100,
                                command=self._on_slider_change)
        self._slider.set(self.editor.zoom_level)
        self._slider.pack(side=tk.LEFT, padx=4)

        return self._frame

    def _tooltip(self, widget, text):
        tip_win = None

        def show(event):
            nonlocal tip_win
            tip_win = tk.Toplevel(widget)
            tip_win.wm_overrideredirect(True)
            tip_win.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            tip_win.configure(bg=self.theme.get_color("tooltip_bg", ""))
            tk.Label(tip_win, text=text,
                     bg=self.theme.get_color("tooltip_bg", ""),
                     fg=self.theme.get_color("text", "primary"),
                     font=("Segoe UI", 8),
                     padx=6, pady=2).pack()

        def hide(event):
            nonlocal tip_win
            if tip_win:
                tip_win.destroy()
                tip_win = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _on_slider_change(self, value):
        if self._updating:
            return
        self._updating = True
        try:
            self.editor.set_zoom(int(float(value)))
            self._update_display()
        finally:
            self._updating = False

    def _on_entry_return(self, event=None):
        text = self._zoom_var.get().strip().replace("%", "")
        try:
            level = int(float(text))
            self.editor.set_zoom(level)
            self._update_display()
        except (ValueError, TypeError):
            self._update_display()

    def _on_preset_select(self, value):
        try:
            level = int(value.replace("%", ""))
            self.editor.set_zoom(level)
            self._update_display()
        except (ValueError, TypeError):
            pass

    def _zoom_in(self):
        self.editor.set_zoom(self.editor.zoom_level + 10)
        self._update_display()

    def _zoom_out(self):
        self.editor.set_zoom(self.editor.zoom_level - 10)
        self._update_display()

    def _fit_page(self):
        self.editor.zoom_fit()
        self._update_display()

    def _fit_width(self):
        self.editor.zoom_width()
        self._update_display()

    def _actual_size(self):
        self.editor.set_zoom(100)
        self._update_display()

    def _update_display(self):
        if self._updating:
            return
        self._updating = True
        try:
            level = self.editor.zoom_level
            if self._zoom_var:
                self._zoom_var.set(f"{level}%")
            if self._slider:
                self._slider.set(level)
            if self._preset_var:
                self._preset_var.set(f"{level}%")
        finally:
            self._updating = False

    def refresh(self):
        self._update_display()

    def handle_ctrl_mousewheel(self, event):
        delta = 10 if event.delta > 0 else -10
        self.editor.set_zoom(self.editor.zoom_level + delta)
        self._update_display()
        return "break"
