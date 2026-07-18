import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except Exception:
    ctk = None


_BUILTIN_THEMES = {
    "Catppuccin Dark": {
        "bg": "#1e1e2e",
        "fg": "#cdd6f4",
        "accent": "#89b4fa",
        "surface": "#313244",
        "border": "#45475a",
        "selection": "#585b70",
        "error": "#f38ba8",
        "warning": "#fab387",
        "success": "#a6e3a1",
        "text_primary": "#cdd6f4",
        "text_secondary": "#a6adc8",
        "panel_bg": "#1e1e2e",
        "ribbon_bg": "#1e1e2e",
        "canvas_bg": "#181825",
        "button_bg": "#45475a",
        "button_fg": "#cdd6f4",
        "hover_bg": "#585b70",
        "active_bg": "#585b70",
        "entry_bg": "#313244",
        "tab_bg": "#313244",
        "separator": "#585b70",
        "dropdown_bg": "#313244",
        "menu_bg": "#313244",
        "tooltip_bg": "#45475a",
        "scrollbar_bg": "#313244",
        "scrollbar_fg": "#585b70",
        "link": "#89b4fa",
        "info": "#74c7ec",
    },
    "Light Professional": {
        "bg": "#f5f5f7",
        "fg": "#1d1d1f",
        "accent": "#0071e3",
        "surface": "#ffffff",
        "border": "#d2d2d7",
        "selection": "#b4d5fe",
        "error": "#d70015",
        "warning": "#b25000",
        "success": "#248a3d",
        "text_primary": "#1d1d1f",
        "text_secondary": "#6e6e73",
        "panel_bg": "#f5f5f7",
        "ribbon_bg": "#fbfbfd",
        "canvas_bg": "#e8e8ed",
        "button_bg": "#e8e8ed",
        "button_fg": "#1d1d1f",
        "hover_bg": "#d2d2d7",
        "active_bg": "#b4d5fe",
        "entry_bg": "#ffffff",
        "tab_bg": "#e8e8ed",
        "separator": "#d2d2d7",
        "dropdown_bg": "#ffffff",
        "menu_bg": "#ffffff",
        "tooltip_bg": "#1d1d1f",
        "scrollbar_bg": "#e8e8ed",
        "scrollbar_fg": "#c7c7cc",
        "link": "#0071e3",
        "info": "#007aff",
    },
    "High Contrast": {
        "bg": "#000000",
        "fg": "#ffffff",
        "accent": "#ffff00",
        "surface": "#1a1a1a",
        "border": "#ffffff",
        "selection": "#0066ff",
        "error": "#ff4444",
        "warning": "#ffaa00",
        "success": "#00ff00",
        "text_primary": "#ffffff",
        "text_secondary": "#cccccc",
        "panel_bg": "#000000",
        "ribbon_bg": "#0a0a0a",
        "canvas_bg": "#111111",
        "button_bg": "#333333",
        "button_fg": "#ffffff",
        "hover_bg": "#555555",
        "active_bg": "#0066ff",
        "entry_bg": "#1a1a1a",
        "tab_bg": "#1a1a1a",
        "separator": "#ffffff",
        "dropdown_bg": "#1a1a1a",
        "menu_bg": "#1a1a1a",
        "tooltip_bg": "#333333",
        "scrollbar_bg": "#333333",
        "scrollbar_fg": "#666666",
        "link": "#66aaff",
        "info": "#66aaff",
    },
    "Blue Steel": {
        "bg": "#1b2838",
        "fg": "#c7d5e0",
        "accent": "#66c0f4",
        "surface": "#2a475e",
        "border": "#3a5a7c",
        "selection": "#4a9eda",
        "error": "#e74c3c",
        "warning": "#f39c12",
        "success": "#2ecc71",
        "text_primary": "#c7d5e0",
        "text_secondary": "#8b9bb4",
        "panel_bg": "#1b2838",
        "ribbon_bg": "#171d25",
        "canvas_bg": "#16202d",
        "button_bg": "#2a475e",
        "button_fg": "#c7d5e0",
        "hover_bg": "#3a5a7c",
        "active_bg": "#4a9eda",
        "entry_bg": "#2a475e",
        "tab_bg": "#2a475e",
        "separator": "#3a5a7c",
        "dropdown_bg": "#2a475e",
        "menu_bg": "#2a475e",
        "tooltip_bg": "#3a5a7c",
        "scrollbar_bg": "#2a475e",
        "scrollbar_fg": "#3a5a7c",
        "link": "#66c0f4",
        "info": "#66c0f4",
    },
}


class ThemeManager:
    _current_theme_name = "Catppuccin Dark"
    _themes = dict(_BUILTIN_THEMES)
    _listeners = []

    @classmethod
    def get_color(cls, category, role=""):
        theme = cls._themes.get(cls._current_theme_name, {})
        combined = f"{category}_{role}" if role else ""
        if combined and combined in theme:
            return theme[combined]
        if role and role in theme:
            return theme[role]
        if category in theme:
            return theme[category]
        if combined:
            return theme.get(combined, "#888888")
        return theme.get(category, "#888888")

    @classmethod
    def get_theme_color(cls, key):
        theme = cls._themes.get(cls._current_theme_name, {})
        return theme.get(key, "#888888")

    @classmethod
    def apply_theme(cls, theme_name):
        if theme_name not in cls._themes:
            return False
        cls._current_theme_name = theme_name
        for callback in cls._listeners:
            try:
                callback(theme_name)
            except Exception:
                pass
        return True

    @classmethod
    def get_current_theme(cls):
        return cls._current_theme_name

    @classmethod
    def list_themes(cls):
        return list(cls._themes.keys())

    @classmethod
    def register_custom_theme(cls, name, colors_dict):
        base = dict(_BUILTIN_THEMES.get("Catppuccin Dark", {}))
        base.update(colors_dict)
        cls._themes[name] = base

    @classmethod
    def on_theme_change(cls, callback):
        cls._listeners.append(callback)

    @classmethod
    def remove_listener(cls, callback):
        if callback in cls._listeners:
            cls._listeners.remove(callback)

    @classmethod
    def _apply_to_tk(cls, root):
        t = cls._themes.get(cls._current_theme_name, {})
        root.configure(bg=t.get("bg", "#1e1e2e"))
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=t.get("bg", "#1e1e2e"),
                        foreground=t.get("fg", "#cdd6f4"))
        style.configure("TFrame", background=t.get("bg", "#1e1e2e"))
        style.configure("TLabel", background=t.get("bg", "#1e1e2e"),
                        foreground=t.get("fg", "#cdd6f4"))
        style.configure("TButton",
                        background=t.get("button_bg", "#45475a"),
                        foreground=t.get("button_fg", "#cdd6f4"),
                        borderwidth=0, padding=4)
        style.map("TButton",
                  background=[("active", t.get("hover_bg", "#585b70"))])
        style.configure("Accent.TButton",
                        background=t.get("accent", "#89b4fa"),
                        foreground=t.get("bg", "#1e1e2e"))
        style.map("Accent.TButton",
                  background=[("active", t.get("hover_bg", "#585b70"))])
        style.configure("Horizontal.TScale",
                        background=t.get("bg", "#1e1e2e"),
                        troughcolor=t.get("surface", "#313244"))
        style.configure("Horizontal.TScrollbar",
                        background=t.get("scrollbar_fg", "#585b70"),
                        troughcolor=t.get("scrollbar_bg", "#313244"))
        style.configure("Vertical.TScrollbar",
                        background=t.get("scrollbar_fg", "#585b70"),
                        troughcolor=t.get("scrollbar_bg", "#313244"))
        style.configure("TCheckbutton",
                        background=t.get("bg", "#1e1e2e"),
                        foreground=t.get("fg", "#cdd6f4"),
                        indicatorcolor=t.get("surface", "#313244"))
        style.configure("TRadiobutton",
                        background=t.get("bg", "#1e1e2e"),
                        foreground=t.get("fg", "#cdd6f4"),
                        indicatorcolor=t.get("surface", "#313244"))
        style.configure("TCombobox",
                        fieldbackground=t.get("entry_bg", "#313244"),
                        background=t.get("button_bg", "#45475a"),
                        foreground=t.get("fg", "#cdd6f4"),
                        arrowcolor=t.get("fg", "#cdd6f4"))
        style.configure("TNotebook",
                        background=t.get("bg", "#1e1e2e"))
        style.configure("TNotebook.Tab",
                        background=t.get("tab_bg", "#313244"),
                        foreground=t.get("fg", "#cdd6f4"),
                        padding=[10, 4])
        style.map("TNotebook.Tab",
                  background=[("selected", t.get("accent", "#89b4fa"))],
                  foreground=[("selected", t.get("bg", "#1e1e2e"))])
