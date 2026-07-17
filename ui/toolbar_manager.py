import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except Exception:
    ctk = None

from ui.theme_manager import ThemeManager


_TOOLBAR_DEFS = {
    "main": {
        "title": "Main Toolbar",
        "default_dock": "top",
        "items": [
            {"text": "\U0001f4c4", "command": "new_temp_document", "tooltip": "New"},
            {"text": "\U0001f4c2", "command": "open_pdf", "tooltip": "Open"},
            {"text": "\U0001f4be", "command": "save_pdf", "tooltip": "Save"},
            {"type": "separator"},
            {"text": "\u21b6", "command": "undo", "tooltip": "Undo"},
            {"text": "\u21b7", "command": "redo", "tooltip": "Redo"},
            {"type": "separator"},
            {"text": "\u2702", "command": "cut_selected", "tooltip": "Cut"},
            {"text": "\U0001f4cb", "command": "copy_selected", "tooltip": "Copy"},
            {"text": "\U0001f4ea", "command": "paste_clipboard", "tooltip": "Paste"},
            {"type": "separator"},
            {"text": "\U0001f5c1", "command": "toggle_selection_mode", "tooltip": "Select"},
            {"text": "\U0001f520", "command": "add_text", "tooltip": "Text"},
            {"text": "\U0001f5bc", "command": "add_image", "tooltip": "Image"},
        ],
    },
    "selection": {
        "title": "Selection",
        "default_dock": "floating",
        "items": [
            {"text": "\U0001f5c1 Select", "command": "toggle_selection_mode", "tooltip": "Select"},
            {"type": "separator"},
            {"text": "\u2716 Delete", "command": "delete_selected_element", "tooltip": "Delete"},
            {"text": "\u21b6 Undo", "command": "undo", "tooltip": "Undo"},
            {"text": "\u21b7 Redo", "command": "redo", "tooltip": "Redo"},
        ],
    },
    "drawing": {
        "title": "Drawing Tools",
        "default_dock": "top",
        "items": [
            {"text": "\u25a1 Rect", "command": "rect", "tooltip": "Rectangle"},
            {"text": "\u25cb Ellipse", "command": "ellipse", "tooltip": "Ellipse"},
            {"text": "\u25b3 Triangle", "command": "triangle", "tooltip": "Triangle"},
            {"text": "\u2571 Line", "command": "line", "tooltip": "Line"},
            {"text": "\u2192 Arrow", "command": "arrow", "tooltip": "Arrow"},
            {"type": "separator"},
            {"text": "\u270d Freehand", "command": "freehand", "tooltip": "Freehand"},
            {"text": "\U0001f4dd Highlight", "command": "highlight", "tooltip": "Highlight"},
        ],
    },
    "format": {
        "title": "Format",
        "default_dock": "top",
        "items": [
            {"text": "B", "command": "toggle_bold", "tooltip": "Bold", "font_style": "bold"},
            {"text": "I", "command": "toggle_italic", "tooltip": "Italic", "font_style": "italic"},
            {"text": "U", "command": "toggle_underline", "tooltip": "Underline", "font_style": "underline"},
            {"type": "separator"},
            {"text": "\u25c0", "command": "align_left", "tooltip": "Align Left"},
            {"text": "\u25ec", "command": "align_center", "tooltip": "Align Center"},
            {"text": "\u25b6", "command": "align_right", "tooltip": "Align Right"},
            {"type": "separator"},
            {"text": "\U0001f3a8", "command": "pick_color", "tooltip": "Text Color"},
        ],
    },
}


class ToolbarManager:
    def __init__(self, editor):
        self.editor = editor
        self.theme = ThemeManager
        self._toolbars = {}
        self._visible_toolbars = set()
        self._floating_offsets = {}

    def create_toolbars(self):
        for name, definition in _TOOLBAR_DEFS.items():
            dock = definition["default_dock"]
            if dock == "floating":
                self._create_floating_toolbar(name, definition)
            else:
                self._create_docked_toolbar(name, definition, dock)

    def _create_docked_toolbar(self, name, definition, dock_side):
        theme = self.theme
        frame = tk.Frame(self.editor.root,
                         bg=theme.get_color("ribbon_bg", ""),
                         bd=0, highlightthickness=1,
                         highlightbackground=theme.get_color("surface", "border"))
        frame.pack(side=tk.TOP if dock_side == "top" else tk.LEFT,
                   fill=tk.X if dock_side == "top" else tk.Y,
                   before=getattr(self.editor, 'ribbon', None))

        self._build_toolbar_content(frame, name, definition)
        self._toolbars[name] = {"frame": frame, "type": "docked", "dock": dock_side}
        self._visible_toolbars.add(name)

    def _create_floating_toolbar(self, name, definition):
        theme = self.theme
        win = tk.Toplevel(self.editor.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=theme.get_color("surface", "bg"))
        win.geometry("+200+200")

        title_bar = tk.Frame(win, bg=theme.get_color("button_bg", ""), bd=0)
        title_bar.pack(fill=tk.X)

        title_label = tk.Label(title_bar, text=f"  {definition['title']}",
                               bg=theme.get_color("button_bg", ""),
                               fg=theme.get_color("text", "primary"),
                               font=("Segoe UI", 8, "bold"))
        title_label.pack(side=tk.LEFT, padx=2, pady=2)

        close_btn = tk.Button(title_bar, text="\u2715",
                              bg=theme.get_color("button_bg", ""),
                              fg=theme.get_color("text", "secondary"),
                              font=("Segoe UI", 8), relief="flat", bd=0,
                              padx=4, cursor="hand2",
                              command=lambda n=name: self.hide_toolbar(n))
        close_btn.pack(side=tk.RIGHT, padx=2)

        content_frame = tk.Frame(win, bg=theme.get_color("surface", "bg"), bd=0)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self._build_toolbar_content(content_frame, name, definition)

        drag_data = {"x": 0, "y": 0}

        def start_drag(event):
            drag_data["x"] = event.x
            drag_data["y"] = event.y

        def do_drag(event):
            x = win.winfo_x() + event.x - drag_data["x"]
            y = win.winfo_y() + event.y - drag_data["y"]
            win.geometry(f"+{x}+{y}")

        title_bar.bind("<ButtonPress-1>", start_drag)
        title_bar.bind("<B1-Motion>", do_drag)
        title_label.bind("<ButtonPress-1>", start_drag)
        title_label.bind("<B1-Motion>", do_drag)

        self._toolbars[name] = {"frame": win, "type": "floating"}
        self._visible_toolbars.add(name)

    def _build_toolbar_content(self, parent, toolbar_name, definition):
        theme = self.theme
        for item_def in definition.get("items", []):
            if item_def.get("type") == "separator":
                orient = tk.VERTICAL if parent.winfo_reqheight() > 40 else tk.HORIZONTAL
                if orient == tk.VERTICAL:
                    sep = tk.Frame(parent, bg=theme.get_color("separator", ""), width=1)
                    sep.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)
                else:
                    sep = tk.Frame(parent, bg=theme.get_color("separator", ""), height=1)
                    sep.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=2)
            else:
                text = item_def.get("text", "")
                tooltip = item_def.get("tooltip", "")
                cmd_name = item_def.get("command", "")
                font_style = item_def.get("font_style", "")

                font = ("Segoe UI", 9)
                if font_style == "bold":
                    font = ("Segoe UI", 9, "bold")
                elif font_style == "italic":
                    font = ("Segoe UI", 9, "italic")
                elif font_style == "underline":
                    font = ("Segoe UI", 9, "underline")

                btn = tk.Button(parent, text=text,
                                bg=theme.get_color("button_bg", ""),
                                fg=theme.get_color("button_fg", ""),
                                font=font,
                                relief="flat", bd=0,
                                padx=6, pady=3,
                                cursor="hand2",
                                command=lambda c=cmd_name: self._execute_command(c))
                btn.pack(side=tk.LEFT, padx=1, pady=1)

                btn.bind("<Enter>",
                         lambda e, b=btn: b.configure(
                             bg=theme.get_color("hover_bg", ""))
                         if b["state"] != "disabled" else None)
                btn.bind("<Leave>",
                         lambda e, b=btn: b.configure(
                             bg=theme.get_color("button_bg", ""))
                         if b["state"] != "disabled" else None)

                if tooltip:
                    self._add_tooltip(btn, tooltip)

    def _add_tooltip(self, widget, text):
        theme = self.theme
        tip_win = None

        def show(event):
            nonlocal tip_win
            tip_win = tk.Toplevel(widget)
            tip_win.wm_overrideredirect(True)
            tip_win.wm_geometry(
                f"+{event.x_root + 12}+{event.y_root + 12}")
            tip_win.configure(bg=theme.get_color("tooltip_bg", ""))
            tk.Label(tip_win, text=text,
                     bg=theme.get_color("tooltip_bg", ""),
                     fg=theme.get_color("text", "primary"),
                     font=("Segoe UI", 8),
                     padx=6, pady=2).pack()

        def hide(event):
            nonlocal tip_win
            if tip_win:
                tip_win.destroy()
                tip_win = None

        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _execute_command(self, cmd_name):
        editor = self.editor
        cmd_map = {
            "new_temp_document": editor.new_document,
            "open_pdf": editor.open_pdf,
            "save_pdf": editor.save_pdf,
            "undo": editor.undo,
            "redo": editor.redo,
            "cut_selected": editor.cut_selected,
            "copy_selected": editor.copy_selected,
            "paste_clipboard": editor.paste_clipboard,
            "toggle_selection_mode": getattr(editor, "toggle_selection_mode",
                                             lambda: editor.set_tool("select")),
            "add_text": getattr(editor, "add_text",
                                lambda: editor.set_tool("text")),
            "add_image": getattr(editor, "add_image",
                                 lambda: editor.insert_image()),
            "delete_selected_element": editor.delete_selected_element,
            "rect": lambda: editor.set_tool("rect"),
            "ellipse": lambda: editor.set_tool("ellipse"),
            "triangle": lambda: editor.set_tool("triangle"),
            "line": lambda: editor.set_tool("line"),
            "arrow": lambda: editor.set_tool("arrow"),
            "freehand": lambda: editor.set_tool("freehand"),
            "highlight": lambda: editor.set_tool("highlight"),
            "toggle_bold": editor.toggle_bold,
            "toggle_italic": editor.toggle_italic,
            "toggle_underline": editor.toggle_underline,
            "align_left": lambda: editor.set_alignment("left"),
            "align_center": lambda: editor.set_alignment("center"),
            "align_right": lambda: editor.set_alignment("right"),
            "pick_color": editor.pick_color,
        }
        cmd = cmd_map.get(cmd_name)
        if cmd:
            cmd()

    def show_toolbar(self, name):
        if name in self._toolbars:
            tb = self._toolbars[name]
            if tb["type"] == "docked":
                tb["frame"].pack(fill=tk.X)
            else:
                tb["frame"].deiconify()
            self._visible_toolbars.add(name)

    def hide_toolbar(self, name):
        if name in self._toolbars:
            tb = self._toolbars[name]
            if tb["type"] == "floating":
                tb["frame"].withdraw()
            else:
                tb["frame"].pack_forget()
            self._visible_toolbars.discard(name)

    def toggle_toolbar(self, name):
        if name in self._visible_toolbars:
            self.hide_toolbar(name)
        else:
            self.show_toolbar(name)

    def is_visible(self, name):
        return name in self._visible_toolbars

    def show_selection_toolbar(self):
        self.show_toolbar("selection")

    def hide_selection_toolbar(self):
        self.hide_toolbar("selection")

    def show_drawing_toolbar(self):
        self.show_toolbar("drawing")

    def hide_drawing_toolbar(self):
        self.hide_toolbar("drawing")
