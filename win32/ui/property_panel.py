import tkinter as tk
from tkinter import ttk, colorchooser
import math

try:
    import customtkinter as ctk
except Exception:
    ctk = None

from ui.theme_manager import ThemeManager


FONT_FAMILIES = [
    "Arial", "Calibri", "Cambria", "Comic Sans MS", "Consolas",
    "Courier New", "Georgia", "Impact", "Lucida Console",
    "Segoe UI", "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana",
]


def _pt_to_inch(pt):
    return round(pt / 72, 3)


def _inch_to_pt(inch):
    return round(inch * 72, 1)


def _fmt_coord(val, unit):
    if unit == "inch":
        return str(_pt_to_inch(val))
    return str(round(val, 1))


def _parse_coord(text, unit):
    try:
        v = float(text)
    except (ValueError, TypeError):
        return None
    return _inch_to_pt(v) if unit == "inch" else round(v, 1)


class _ColorPickerButton(tk.Canvas):
    def __init__(self, parent, color="#000000", on_change=None, size=18, **kw):
        super().__init__(parent, width=size, height=size,
                         highlightthickness=0, bd=0, cursor="hand2", **kw)
        self._color = color
        self._size = size
        self._on_change = on_change
        self._draw()
        self.bind("<Button-1>", self._pick)

    def _draw(self):
        self.delete("all")
        self.create_rectangle(1, 1, self._size - 1, self._size - 1,
                              fill=self._color, outline="#585b70", width=1)

    def get_color(self):
        return self._color

    def set_color(self, color):
        self._color = color
        self._draw()

    def _pick(self, event=None):
        result = colorchooser.askcolor(initialcolor=self._color, parent=self)
        if result and result[1]:
            self._color = result[1]
            self._draw()
            if self._on_change:
                self._on_change(self._color)


class _PropertyRow(tk.Frame):
    def __init__(self, parent, label, theme, height=24):
        super().__init__(parent, bg=theme.get_color("panel", "bg"), height=height)
        self.pack_propagate(False)
        self._label = tk.Label(self, text=label, bg=theme.get_color("panel", "bg"),
                               fg=theme.get_color("text", "secondary"),
                               font=("Segoe UI", 8), anchor="w", width=10)
        self._label.pack(side=tk.LEFT, padx=(8, 2))
        self._value_frame = tk.Frame(self, bg=theme.get_color("panel", "bg"))
        self._value_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 8))

    @property
    def value_frame(self):
        return self._value_frame


class PropertyPanel:
    def __init__(self, editor, parent):
        self.editor = editor
        self.parent = parent
        self.theme = ThemeManager
        self._coord_unit = "pt"
        self._suppress_update = False

        self.frame = tk.Frame(parent, bg=self.theme.get_color("panel", "bg"),
                              bd=0, highlightthickness=0)
        self.frame.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(self.frame, bg=self.theme.get_color("panel", "bg"), bd=0)
        header.pack(fill=tk.X, padx=0, pady=0)

        tk.Label(header, text="Properties",
                 bg=self.theme.get_color("panel", "bg"),
                 fg=self.theme.get_color("text", "primary"),
                 font=("Segoe UI", 10, "bold"),
                 anchor="w").pack(side=tk.LEFT, padx=8, pady=(6, 2))

        unit_frame = tk.Frame(header, bg=self.theme.get_color("panel", "bg"))
        unit_frame.pack(side=tk.RIGHT, padx=8, pady=(6, 2))

        self._unit_var = tk.StringVar(value="pt")
        pt_rb = tk.Radiobutton(unit_frame, text="pt", variable=self._unit_var,
                               value="pt", bg=self.theme.get_color("panel", "bg"),
                               fg=self.theme.get_color("text", "secondary"),
                               selectcolor=self.theme.get_color("surface", "bg"),
                               activebackground=self.theme.get_color("panel", "bg"),
                               activeforeground=self.theme.get_color("text", "primary"),
                               font=("Segoe UI", 7), indicatoron=False,
                               padx=4, pady=1, cursor="hand2",
                               command=self._toggle_unit)
        pt_rb.pack(side=tk.LEFT)
        in_rb = tk.Radiobutton(unit_frame, text="in", variable=self._unit_var,
                               value="inch", bg=self.theme.get_color("panel", "bg"),
                               fg=self.theme.get_color("text", "secondary"),
                               selectcolor=self.theme.get_color("surface", "bg"),
                               activebackground=self.theme.get_color("panel", "bg"),
                               activeforeground=self.theme.get_color("text", "primary"),
                               font=("Segoe UI", 7), indicatoron=False,
                               padx=4, pady=1, cursor="hand2",
                               command=self._toggle_unit)
        in_rb.pack(side=tk.LEFT)

        ttk.Separator(self.frame, orient="horizontal").pack(fill=tk.X)

        self._scroll_canvas = tk.Canvas(self.frame,
                                        bg=self.theme.get_color("panel", "bg"),
                                        bd=0, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL,
                                        command=self._scroll_canvas.yview)
        self._inner = tk.Frame(self._scroll_canvas,
                               bg=self.theme.get_color("panel", "bg"))
        self._inner.bind("<Configure>",
                         lambda e: self._scroll_canvas.configure(
                             scrollregion=self._scroll_canvas.bbox("all")))
        self._scroll_canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._scroll_canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._scroll_canvas.bind("<MouseWheel>", self._on_mousewheel)

        self._no_selection_frame = tk.Frame(self._inner,
                                           bg=self.theme.get_color("panel", "bg"))
        self._no_selection_frame.pack(fill=tk.BOTH, expand=True, pady=40)
        tk.Label(self._no_selection_frame, text="\u25c7",
                 bg=self.theme.get_color("panel", "bg"),
                 fg=self.theme.get_color("surface", "border"),
                 font=("Segoe UI", 28)).pack()
        tk.Label(self._no_selection_frame, text="No element selected",
                 bg=self.theme.get_color("panel", "bg"),
                 fg=self.theme.get_color("text", "secondary"),
                 font=("Segoe UI", 9)).pack(pady=(4, 0))
        tk.Label(self._no_selection_frame, text="Click an element to inspect its properties",
                 bg=self.theme.get_color("panel", "bg"),
                 fg=self.theme.get_color("surface", "border"),
                 font=("Segoe UI", 8)).pack(pady=(2, 0))

        self._prop_frame = tk.Frame(self._inner,
                                    bg=self.theme.get_color("panel", "bg"))

        self._current_type = None

    def _on_mousewheel(self, event):
        self._scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _toggle_unit(self):
        self._coord_unit = self._unit_var.get()
        self.refresh()

    def refresh(self):
        for w in self._prop_frame.winfo_children():
            w.destroy()

        if self.editor.selected_element is None:
            self._prop_frame.pack_forget()
            self._no_selection_frame.pack(fill=tk.BOTH, expand=True, pady=40)
            self._current_type = None
            return

        self._no_selection_frame.pack_forget()
        self._prop_frame.pack(fill=tk.BOTH, expand=True)

        idx = self.editor.selected_element
        if idx is None or idx >= len(self.editor.elements):
            return

        elem = self.editor.elements[idx]
        etype = getattr(elem, "type_name", type(elem).__name__)

        self._current_type = etype

        section_title = tk.Label(self._prop_frame,
                                 text=f"  {etype.upper()}",
                                 bg=self.theme.get_color("accent", "bg"),
                                 fg=self.theme.get_color("accent", "fg"),
                                 font=("Segoe UI", 8, "bold"),
                                 anchor="w", pady=3)
        section_title.pack(fill=tk.X, padx=0, pady=(4, 0))

        builder = self._get_builder(etype)
        if builder:
            builder(elem)

        self._add_generic_section(elem)

    def _get_builder(self, etype):
        builders = {
            "text": self._build_text_props,
            "image": self._build_image_props,
            "shape": self._build_shape_props,
            "line": self._build_line_props,
            "highlight": self._build_highlight_props,
            "annotation": self._build_highlight_props,
            "stamp": self._build_stamp_props,
            "signature": self._build_signature_props,
            "formfield": self._build_formfield_props,
            "watermark": self._build_watermark_props,
            "link": self._build_link_props,
            "note": self._build_note_props,
            "redact": self._build_redact_props,
            "headerfooter": self._build_headerfooter_props,
        }
        return builders.get(etype)

    def _add_text_row(self, parent, label, text_var, on_change=None):
        row = _PropertyRow(parent, label, self.theme)
        row.pack(fill=tk.X, pady=1)
        entry = tk.Entry(row.value_frame, textvariable=text_var,
                         bg=self.theme.get_color("surface", "bg"),
                         fg=self.theme.get_color("text", "primary"),
                         insertbackground=self.theme.get_color("text", "primary"),
                         font=("Segoe UI", 8), relief="flat", bd=3,
                         highlightthickness=1,
                         highlightbackground=self.theme.get_color("surface", "border"),
                         highlightcolor=self.theme.get_color("accent", "bg"))
        entry.pack(fill=tk.X, expand=True)
        if on_change:
            text_var.trace_add("write", lambda *a: on_change())
        return entry

    def _add_entry_row(self, parent, label, value, on_change=None, width=6, **kw):
        row = _PropertyRow(parent, label, self.theme)
        row.pack(fill=tk.X, pady=1)
        var = tk.StringVar(value=str(value))
        entry = tk.Entry(row.value_frame, textvariable=var, width=width,
                         bg=self.theme.get_color("surface", "bg"),
                         fg=self.theme.get_color("text", "primary"),
                         insertbackground=self.theme.get_color("text", "primary"),
                         font=("Segoe UI", 8), relief="flat", bd=3,
                         highlightthickness=1,
                         highlightbackground=self.theme.get_color("surface", "border"),
                         highlightcolor=self.theme.get_color("accent", "bg"),
                         **kw)
        entry.pack(side=tk.LEFT)
        if on_change:
            var.trace_add("write", lambda *a: on_change(var.get()))
        return var

    def _add_combo_row(self, parent, label, values, current, on_change=None):
        row = _PropertyRow(parent, label, self.theme)
        row.pack(fill=tk.X, pady=1)
        var = tk.StringVar(value=str(current))
        combo = ttk.Combobox(row.value_frame, textvariable=var, values=values,
                             width=14, state="readonly",
                             font=("Segoe UI", 8))
        combo.pack(fill=tk.X, expand=True)
        if on_change:
            combo.bind("<<ComboboxSelected>>", lambda e: on_change(var.get()))
        return var

    def _add_check_row(self, parent, label, value, on_change=None):
        row = _PropertyRow(parent, label, self.theme)
        row.pack(fill=tk.X, pady=1)
        var = tk.BooleanVar(value=bool(value))
        cb = tk.Checkbutton(row.value_frame, variable=var,
                            bg=self.theme.get_color("panel", "bg"),
                            fg=self.theme.get_color("text", "primary"),
                            selectcolor=self.theme.get_color("surface", "bg"),
                            activebackground=self.theme.get_color("panel", "bg"),
                            activeforeground=self.theme.get_color("text", "primary"),
                            font=("Segoe UI", 8))
        cb.pack(side=tk.LEFT)
        if on_change:
            var.trace_add("write", lambda *a: on_change(var.get()))
        return var

    def _add_color_row(self, parent, label, color, on_change=None):
        row = _PropertyRow(parent, label, self.theme)
        row.pack(fill=tk.X, pady=1)
        hex_var = tk.StringVar(value=color or "#000000")
        entry = tk.Entry(row.value_frame, textvariable=hex_var, width=8,
                         bg=self.theme.get_color("surface", "bg"),
                         fg=self.theme.get_color("text", "primary"),
                         insertbackground=self.theme.get_color("text", "primary"),
                         font=("Segoe UI", 8), relief="flat", bd=3,
                         highlightthickness=1,
                         highlightbackground=self.theme.get_color("surface", "border"),
                         highlightcolor=self.theme.get_color("accent", "bg"))
        entry.pack(side=tk.LEFT)

        picker = _ColorPickerButton(row.value_frame, color=color or "#000000",
                                    size=18)
        picker.pack(side=tk.LEFT, padx=(4, 0))

        def on_color_change(c):
            hex_var.set(c)
            if on_change:
                on_change(c)

        picker._on_change = on_color_change

        def on_hex_change(*a):
            c = hex_var.get()
            if len(c) == 7 and c.startswith("#"):
                picker.set_color(c)
                if on_change:
                    on_change(c)

        hex_var.trace_add("write", on_hex_change)
        return hex_var, picker

    def _add_coord_row(self, parent, label, x_val, y_val, on_x=None, on_y=None):
        row = tk.Frame(parent, bg=self.theme.get_color("panel", "bg"), height=24)
        row.pack(fill=tk.X, pady=1)
        row.pack_propagate(False)
        tk.Label(row, text=label, bg=self.theme.get_color("panel", "bg"),
                 fg=self.theme.get_color("text", "secondary"),
                 font=("Segoe UI", 8), anchor="w", width=10).pack(side=tk.LEFT, padx=(8, 2))

        coords_frame = tk.Frame(row, bg=self.theme.get_color("panel", "bg"))
        coords_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 8))

        for lbl, val, on_cb in [("X", x_val, on_x), ("Y", y_val, on_y)]:
            tk.Label(coords_frame, text=lbl, bg=self.theme.get_color("panel", "bg"),
                     fg=self.theme.get_color("text", "secondary"),
                     font=("Segoe UI", 7)).pack(side=tk.LEFT, padx=(2, 0))
            var = tk.StringVar(value=_fmt_coord(val, self._coord_unit))
            e = tk.Entry(coords_frame, textvariable=var, width=6,
                         bg=self.theme.get_color("surface", "bg"),
                         fg=self.theme.get_color("text", "primary"),
                         insertbackground=self.theme.get_color("text", "primary"),
                         font=("Segoe UI", 8), relief="flat", bd=3,
                         highlightthickness=1,
                         highlightbackground=self.theme.get_color("surface", "border"),
                         highlightcolor=self.theme.get_color("accent", "bg"))
            e.pack(side=tk.LEFT, padx=(1, 2))
            if on_cb:
                var.trace_add("write", lambda *a, v=var, cb=on_cb: cb(v.get()))

    def _add_size_row(self, parent, label, w_val, h_val, on_w=None, on_h=None):
        row = tk.Frame(parent, bg=self.theme.get_color("panel", "bg"), height=24)
        row.pack(fill=tk.X, pady=1)
        row.pack_propagate(False)
        tk.Label(row, text=label, bg=self.theme.get_color("panel", "bg"),
                 fg=self.theme.get_color("text", "secondary"),
                 font=("Segoe UI", 8), anchor="w", width=10).pack(side=tk.LEFT, padx=(8, 2))

        size_frame = tk.Frame(row, bg=self.theme.get_color("panel", "bg"))
        size_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 8))

        for lbl, val, on_cb in [("W", w_val, on_w), ("H", h_val, on_h)]:
            tk.Label(size_frame, text=lbl, bg=self.theme.get_color("panel", "bg"),
                     fg=self.theme.get_color("text", "secondary"),
                     font=("Segoe UI", 7)).pack(side=tk.LEFT, padx=(2, 0))
            var = tk.StringVar(value=_fmt_coord(val, self._coord_unit))
            e = tk.Entry(size_frame, textvariable=var, width=6,
                         bg=self.theme.get_color("surface", "bg"),
                         fg=self.theme.get_color("text", "primary"),
                         insertbackground=self.theme.get_color("text", "primary"),
                         font=("Segoe UI", 8), relief="flat", bd=3,
                         highlightthickness=1,
                         highlightbackground=self.theme.get_color("surface", "border"),
                         highlightcolor=self.theme.get_color("accent", "bg"))
            e.pack(side=tk.LEFT, padx=(1, 2))
            if on_cb:
                var.trace_add("write", lambda *a, v=var, cb=on_cb: cb(v.get()))

    def _commit(self, elem, attr, value):
        if self._suppress_update:
            return
        self.editor.undo_manager.save_state(self.editor.elements)
        setattr(elem, attr, value)
        self.editor.canvas_manager.update_preview()

    def _build_text_props(self, elem):
        p = self._prop_frame

        text_var = tk.StringVar(value=elem.text)
        self._add_text_row(p, "Content", text_var,
                           on_change=lambda: self._commit(elem, "text", text_var.get()))

        self._add_combo_row(p, "Font", FONT_FAMILIES, elem.font_name,
                            on_change=lambda v: self._commit(elem, "font_name", v))

        self._add_entry_row(p, "Size", elem.size,
                            on_change=lambda v: self._commit(elem, "size", int(v) if v.isdigit() else elem.size))

        btn_frame = tk.Frame(p, bg=self.theme.get_color("panel", "bg"), height=24)
        btn_frame.pack(fill=tk.X, pady=1)
        btn_frame.pack_propagate(False)
        tk.Label(btn_frame, text="Style", bg=self.theme.get_color("panel", "bg"),
                 fg=self.theme.get_color("text", "secondary"),
                 font=("Segoe UI", 8), anchor="w", width=10).pack(side=tk.LEFT, padx=(8, 2))

        for label, attr, style_flag in [("B", "bold", "bold"),
                                        ("I", "italic", "italic"),
                                        ("U", "underline", "underline")]:
            var = tk.BooleanVar(value=getattr(elem, attr, False))
            btn = tk.Button(btn_frame, text=label,
                            bg=self.theme.get_color("button", "bg") if not var.get() else self.theme.get_color("accent", "bg"),
                            fg=self.theme.get_color("button", "fg"),
                            font=("Segoe UI", 9, style_flag),
                            relief="flat", bd=0, width=3, cursor="hand2",
                            command=lambda a=attr, v=var, b=btn, s=style_flag: self._toggle_style(elem, a, v, b, s))
            btn.pack(side=tk.LEFT, padx=1)

        self._add_color_row(p, "Color", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))

        self._add_combo_row(p, "Align", ["left", "center", "right"], elem.alignment,
                            on_change=lambda v: self._commit(elem, "alignment", v))

    def _toggle_style(self, elem, attr, var, btn, style_flag):
        new_val = not var.get()
        var.set(new_val)
        self._commit(elem, attr, new_val)
        if new_val:
            btn.configure(bg=self.theme.get_color("accent", "bg"))
        else:
            btn.configure(bg=self.theme.get_color("button", "bg"))

    def _build_image_props(self, elem):
        p = self._prop_frame

        path_var = tk.StringVar(value=elem.path)
        row = _PropertyRow(p, "Source", self.theme)
        row.pack(fill=tk.X, pady=1)
        entry = tk.Entry(row.value_frame, textvariable=path_var,
                         bg=self.theme.get_color("surface", "bg"),
                         fg=self.theme.get_color("text", "secondary"),
                         font=("Segoe UI", 7), relief="flat", bd=3,
                         state="readonly")
        entry.pack(fill=tk.X, expand=True)

        self._add_coord_row(p, "Position", elem.x, elem.y,
                            on_x=lambda v: self._on_coord_change(elem, "x", v),
                            on_y=lambda v: self._on_coord_change(elem, "y", v))

        self._add_size_row(p, "Size", elem.w, elem.h,
                           on_w=lambda v: self._on_size_change(elem, "w", v),
                           on_h=lambda v: self._on_size_change(elem, "h", v))

        self._add_entry_row(p, "Rotation",
                            getattr(elem, "rotation", 0),
                            on_change=lambda v: self._commit(elem, "rotation", float(v) if v else 0))

    def _build_shape_props(self, elem):
        p = self._prop_frame

        type_row = _PropertyRow(p, "Type", self.theme)
        type_row.pack(fill=tk.X, pady=1)
        tk.Label(type_row.value_frame, text=elem.shape_type,
                 bg=self.theme.get_color("surface", "bg"),
                 fg=self.theme.get_color("text", "primary"),
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(side=tk.LEFT)

        self._add_color_row(p, "Stroke", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))
        self._add_color_row(p, "Fill", elem.fill_color,
                            on_change=lambda c: self._commit(elem, "fill_color", c))

        self._add_check_row(p, "Filled", elem.filled,
                            on_change=lambda v: self._commit(elem, "filled", v))

        self._add_entry_row(p, "Stroke W", elem.stroke_width,
                            on_change=lambda v: self._commit(elem, "stroke_width", int(v) if v.isdigit() else elem.stroke_width))

        self._add_coord_row(p, "Position", elem.x, elem.y,
                            on_x=lambda v: self._on_coord_change(elem, "x", v),
                            on_y=lambda v: self._on_coord_change(elem, "y", v))

        self._add_size_row(p, "Size", elem.w, elem.h,
                           on_w=lambda v: self._on_size_change(elem, "w", v),
                           on_h=lambda v: self._on_size_change(elem, "h", v))

    def _build_line_props(self, elem):
        p = self._prop_frame

        self._add_coord_row(p, "Start", elem.x1, elem.y1,
                            on_x=lambda v: self._on_coord_change(elem, "x1", v),
                            on_y=lambda v: self._on_coord_change(elem, "y1", v))

        self._add_coord_row(p, "End", elem.x2, elem.y2,
                            on_x=lambda v: self._on_coord_change(elem, "x2", v),
                            on_y=lambda v: self._on_coord_change(elem, "y2", v))

        self._add_color_row(p, "Color", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))

        self._add_entry_row(p, "Width", elem.width,
                            on_change=lambda v: self._commit(elem, "width", int(v) if v.isdigit() else elem.width))

        arrow_row = _PropertyRow(p, "Arrow", self.theme)
        arrow_row.pack(fill=tk.X, pady=1)
        arrow_var = tk.StringVar(value=getattr(elem, "arrow_style", "none"))
        ttk.Combobox(arrow_row.value_frame, textvariable=arrow_var,
                     values=["none", "start", "end", "both"],
                     width=10, state="readonly",
                     font=("Segoe UI", 8)).pack(fill=tk.X, expand=True)

    def _build_highlight_props(self, elem):
        p = self._prop_frame

        self._add_color_row(p, "Color", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))

        opacity_var = tk.StringVar(value=str(round(elem.opacity, 2)))
        self._add_entry_row(p, "Opacity", opacity_var.get(),
                            on_change=lambda v: self._on_opacity_change(elem, v))

        self._add_coord_row(p, "Position", elem.x, elem.y,
                            on_x=lambda v: self._on_coord_change(elem, "x", v),
                            on_y=lambda v: self._on_coord_change(elem, "y", v))

        self._add_size_row(p, "Size", elem.w, elem.h,
                           on_w=lambda v: self._on_size_change(elem, "w", v),
                           on_h=lambda v: self._on_size_change(elem, "h", v))

    def _build_stamp_props(self, elem):
        p = self._prop_frame

        text_var = tk.StringVar(value=elem.text)
        self._add_text_row(p, "Text", text_var,
                           on_change=lambda: self._commit(elem, "text", text_var.get()))

        self._add_entry_row(p, "Font Size", elem.font_size,
                            on_change=lambda v: self._commit(elem, "font_size", int(v) if v.isdigit() else elem.font_size))

        self._add_entry_row(p, "Rotation", elem.rotation,
                            on_change=lambda v: self._commit(elem, "rotation", float(v) if v else 0))

        self._add_color_row(p, "Color", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))

        self._add_entry_row(p, "Opacity", round(elem.opacity, 2),
                            on_change=lambda v: self._on_opacity_change(elem, v))

        self._add_combo_row(p, "Font", FONT_FAMILIES, elem.font_name,
                            on_change=lambda v: self._commit(elem, "font_name", v))

        self._add_check_row(p, "Bold", elem.bold,
                            on_change=lambda v: self._commit(elem, "bold", v))

        self._add_coord_row(p, "Position", elem.x, elem.y,
                            on_x=lambda v: self._on_coord_change(elem, "x", v),
                            on_y=lambda v: self._on_coord_change(elem, "y", v))

    def _build_signature_props(self, elem):
        p = self._prop_frame

        if elem.text:
            text_var = tk.StringVar(value=elem.text)
            self._add_text_row(p, "Text", text_var,
                               on_change=lambda: self._commit(elem, "text", text_var.get()))

        self._add_color_row(p, "Color", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))

        self._add_coord_row(p, "Position", elem.x, elem.y,
                            on_x=lambda v: self._on_coord_change(elem, "x", v),
                            on_y=lambda v: self._on_coord_change(elem, "y", v))

        self._add_size_row(p, "Size", elem.w, elem.h,
                           on_w=lambda v: self._on_size_change(elem, "w", v),
                           on_h=lambda v: self._on_size_change(elem, "h", v))

    def _build_formfield_props(self, elem):
        p = self._prop_frame

        type_row = _PropertyRow(p, "Type", self.theme)
        type_row.pack(fill=tk.X, pady=1)
        tk.Label(type_row.value_frame, text=elem.field_type,
                 bg=self.theme.get_color("surface", "bg"),
                 fg=self.theme.get_color("text", "primary"),
                 font=("Segoe UI", 8), anchor="w").pack(side=tk.LEFT)

        name_var = tk.StringVar(value=elem.field_name)
        self._add_text_row(p, "Name", name_var,
                           on_change=lambda: self._commit(elem, "field_name", name_var.get()))

        val_var = tk.StringVar(value=elem.value)
        self._add_text_row(p, "Value", val_var,
                           on_change=lambda: self._commit(elem, "value", val_var.get()))

        self._add_check_row(p, "Required", elem.required,
                            on_change=lambda v: self._commit(elem, "required", v))

        self._add_entry_row(p, "Font Size", elem.font_size,
                            on_change=lambda v: self._commit(elem, "font_size", int(v) if v.isdigit() else elem.font_size))

        self._add_coord_row(p, "Position", elem.x, elem.y,
                            on_x=lambda v: self._on_coord_change(elem, "x", v),
                            on_y=lambda v: self._on_coord_change(elem, "y", v))

        self._add_size_row(p, "Size", elem.w, elem.h,
                           on_w=lambda v: self._on_size_change(elem, "w", v),
                           on_h=lambda v: self._on_size_change(elem, "h", v))

    def _build_watermark_props(self, elem):
        p = self._prop_frame

        text_var = tk.StringVar(value=elem.text)
        self._add_text_row(p, "Text", text_var,
                           on_change=lambda: self._commit(elem, "text", text_var.get()))

        self._add_entry_row(p, "Size", elem.size,
                            on_change=lambda v: self._commit(elem, "size", int(v) if v.isdigit() else elem.size))

        self._add_entry_row(p, "Rotation", elem.rotation,
                            on_change=lambda v: self._commit(elem, "rotation", float(v) if v else 0))

        self._add_entry_row(p, "Opacity", round(elem.opacity, 2),
                            on_change=lambda v: self._on_opacity_change(elem, v))

        self._add_color_row(p, "Color", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))

    def _build_link_props(self, elem):
        p = self._prop_frame

        url_var = tk.StringVar(value=elem.url)
        self._add_text_row(p, "URL", url_var,
                           on_change=lambda: self._commit(elem, "url", url_var.get()))

        text_var = tk.StringVar(value=elem.text)
        self._add_text_row(p, "Label", text_var,
                           on_change=lambda: self._commit(elem, "text", text_var.get()))

        self._add_color_row(p, "Color", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))

        self._add_coord_row(p, "Position", elem.x, elem.y,
                            on_x=lambda v: self._on_coord_change(elem, "x", v),
                            on_y=lambda v: self._on_coord_change(elem, "y", v))

        self._add_size_row(p, "Size", elem.w, elem.h,
                           on_w=lambda v: self._on_size_change(elem, "w", v),
                           on_h=lambda v: self._on_size_change(elem, "h", v))

    def _build_note_props(self, elem):
        p = self._prop_frame

        text_var = tk.StringVar(value=elem.text)
        self._add_text_row(p, "Note", text_var,
                           on_change=lambda: self._commit(elem, "text", text_var.get()))

        author_var = tk.StringVar(value=elem.author)
        self._add_text_row(p, "Author", author_var,
                           on_change=lambda: self._commit(elem, "author", author_var.get()))

        self._add_color_row(p, "Color", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))

    def _build_redact_props(self, elem):
        p = self._prop_frame

        label_var = tk.StringVar(value=elem.label)
        self._add_text_row(p, "Label", label_var,
                           on_change=lambda: self._commit(elem, "label", label_var.get()))

        self._add_color_row(p, "Color", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))

        self._add_coord_row(p, "Position", elem.x, elem.y,
                            on_x=lambda v: self._on_coord_change(elem, "x", v),
                            on_y=lambda v: self._on_coord_change(elem, "y", v))

        self._add_size_row(p, "Size", elem.w, elem.h,
                           on_w=lambda v: self._on_size_change(elem, "w", v),
                           on_h=lambda v: self._on_size_change(elem, "h", v))

    def _build_headerfooter_props(self, elem):
        p = self._prop_frame

        text_var = tk.StringVar(value=elem.text)
        self._add_text_row(p, "Text", text_var,
                           on_change=lambda: self._commit(elem, "text", text_var.get()))

        self._add_entry_row(p, "Size", elem.size,
                            on_change=lambda v: self._commit(elem, "size", int(v) if v.isdigit() else elem.size))

        self._add_color_row(p, "Color", elem.color,
                            on_change=lambda c: self._commit(elem, "color", c))

        self._add_combo_row(p, "Position",
                            ["header-left", "header-center", "header-right",
                             "footer-left", "footer-center", "footer-right"],
                            elem.position,
                            on_change=lambda v: self._commit(elem, "position", v))

    def _add_generic_section(self, elem):
        p = self._prop_frame

        sep = tk.Frame(p, bg=self.theme.get_color("surface", "border"), height=1)
        sep.pack(fill=tk.X, padx=8, pady=(8, 4))

        gen_label = tk.Label(p, text="  GENERAL",
                             bg=self.theme.get_color("surface", "bg"),
                             fg=self.theme.get_color("text", "secondary"),
                             font=("Segoe UI", 7, "bold"), anchor="w", pady=2)
        gen_label.pack(fill=tk.X)

        bx, by, bw, bh = elem.get_bounds()
        self._add_coord_row(p, "Position", bx, by,
                            on_x=lambda v: self._on_coord_change(elem, "x", v),
                            on_y=lambda v: self._on_coord_change(elem, "y", v))

        if hasattr(elem, "w") and hasattr(elem, "h"):
            self._add_size_row(p, "Size", bw, bh,
                               on_w=lambda v: self._on_size_change(elem, "w", v),
                               on_h=lambda v: self._on_size_change(elem, "h", v))

        rot = getattr(elem, "rotation", 0)
        self._add_entry_row(p, "Rotation", rot,
                            on_change=lambda v: self._commit(elem, "rotation", float(v) if v else 0))

        self._add_entry_row(p, "Opacity", round(getattr(elem, "opacity", 1.0), 2),
                            on_change=lambda v: self._on_opacity_change(elem, v))

        self._add_check_row(p, "Locked", getattr(elem, "locked", False),
                            on_change=lambda v: self._commit(elem, "locked", v))

        name_var = tk.StringVar(value=getattr(elem, "name", ""))
        self._add_text_row(p, "Name", name_var,
                           on_change=lambda: self._commit(elem, "name", name_var.get()))

        page_var = tk.StringVar(value=str(elem.page))
        self._add_entry_row(p, "Page", page_var.get(), width=4,
                            on_change=lambda v: self._commit(elem, "page", int(v) if v.isdigit() else elem.page))

    def _on_coord_change(self, elem, attr, raw_value):
        val = _parse_coord(raw_value, self._coord_unit)
        if val is not None:
            self._commit(elem, attr, val)

    def _on_size_change(self, elem, attr, raw_value):
        val = _parse_coord(raw_value, self._coord_unit)
        if val is not None and val > 0:
            self._commit(elem, attr, val)

    def _on_opacity_change(self, elem, raw_value):
        try:
            v = float(raw_value)
            v = max(0.0, min(1.0, v))
            self._commit(elem, "opacity", v)
        except (ValueError, TypeError):
            pass
