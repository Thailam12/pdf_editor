import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except Exception:
    ctk = None

from ui.theme_manager import ThemeManager

_SHORTCUTS = [
    ("File", [
        ("New Document", "Ctrl+N"),
        ("Open PDF", "Ctrl+O"),
        ("Save", "Ctrl+S"),
        ("Save As", "Ctrl+Shift+S"),
        ("Print", "Ctrl+P"),
        ("Close", "Alt+F4"),
    ]),
    ("Edit", [
        ("Undo", "Ctrl+Z"),
        ("Redo", "Ctrl+Y"),
        ("Cut", "Ctrl+X"),
        ("Copy", "Ctrl+C"),
        ("Paste", "Ctrl+V"),
        ("Select All", "Ctrl+A"),
        ("Deselect", "Escape"),
        ("Delete", "Delete"),
        ("Find & Replace", "Ctrl+H"),
    ]),
    ("View", [
        ("Zoom In", "Ctrl+="),
        ("Zoom Out", "Ctrl+-"),
        ("Fit Page", "Ctrl+0"),
        ("Fit Width", "Ctrl+Shift+0"),
        ("Toggle Grid", "Ctrl+G"),
        ("Actual Size", "Ctrl+1"),
    ]),
    ("Tools", [
        ("Selection Tool", "V"),
        ("Text Tool", "T"),
        ("Rectangle", "R"),
        ("Ellipse", "E"),
        ("Line", "L"),
        ("Arrow", "A"),
        ("Highlight", "H"),
        ("Freehand", "F"),
        ("Eraser", "X"),
    ]),
    ("Navigation", [
        ("Previous Page", "Left / Page Up"),
        ("Next Page", "Right / Page Down"),
        ("First Page", "Home"),
        ("Last Page", "End"),
        ("Scroll Up", "Mouse Wheel Up"),
        ("Scroll Down", "Mouse Wheel Down"),
    ]),
    ("General", [
        ("Show Shortcuts", "F1"),
        ("Toggle Shortcuts", "Ctrl+/"),
        ("Help", "F1"),
    ]),
]


class ShortcutOverlay:
    def __init__(self, editor, parent=None):
        self.editor = editor
        self.theme = ThemeManager
        self._overlay = None
        self._visible = False
        self._search_var = None
        self._parent = parent or editor.root

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def show(self):
        if self._visible:
            return
        self._visible = True
        self._build_overlay()

    def hide(self):
        if not self._visible:
            return
        self._visible = False
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None

    def _build_overlay(self):
        theme = self.theme
        self._overlay = tk.Toplevel(self._parent)
        self._overlay.overrideredirect(True)
        self._overlay.attributes("-topmost", True)
        self._overlay.configure(bg="#000000")

        pw = self._parent.winfo_width()
        ph = self._parent.winfo_height()
        px = self._parent.winfo_rootx()
        py = self._parent.winfo_rooty()

        ow = min(720, pw - 80)
        oh = min(560, ph - 80)
        ox = px + (pw - ow) // 2
        oy = py + (ph - oh) // 2

        self._overlay.geometry(f"{ow}x{oh}+{ox}+{oy}")
        self._overlay.attributes("-alpha", 0.95)

        container = tk.Frame(self._overlay, bg="#11111b", bd=0,
                             highlightthickness=1,
                             highlightbackground=theme.get_color("surface", "border"))
        container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        header = tk.Frame(container, bg="#181825", bd=0)
        header.pack(fill=tk.X)

        tk.Label(header, text="\u2328  Keyboard Shortcuts",
                 bg="#181825", fg=theme.get_color("text", "primary"),
                 font=("Segoe UI", 12, "bold"),
                 anchor="w", padx=16, pady=10).pack(side=tk.LEFT)

        close_btn = tk.Button(header, text="\u2715",
                              bg="#181825",
                              fg=theme.get_color("text", "secondary"),
                              font=("Segoe UI", 12),
                              relief="flat", bd=0, cursor="hand2",
                              padx=12, pady=6,
                              command=self.hide)
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg=theme.get_color("danger", "fg")))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg=theme.get_color("text", "secondary")))

        search_frame = tk.Frame(container, bg="#181825", bd=0)
        search_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        search_icon = tk.Label(search_frame, text="\U0001f50d",
                               bg="#181825",
                               fg=theme.get_color("text", "secondary"),
                               font=("Segoe UI", 10))
        search_icon.pack(side=tk.LEFT, padx=(0, 6))

        self._search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self._search_var,
                                bg=theme.get_color("surface", "bg"),
                                fg=theme.get_color("text", "primary"),
                                insertbackground=theme.get_color("text", "primary"),
                                font=("Segoe UI", 10),
                                relief="flat", bd=0,
                                highlightthickness=1,
                                highlightbackground=theme.get_color("surface", "border"),
                                highlightcolor=theme.get_color("accent", "bg"))
        search_entry.pack(fill=tk.X, ipady=4)
        search_entry.focus_set()
        self._search_var.trace_add("write", lambda *a: self._filter_shortcuts())

        self._content_frame = tk.Frame(container, bg="#11111b", bd=0)
        self._content_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        self._build_shortcut_list()

        self._overlay.bind("<Escape>", lambda e: self.hide())
        self._overlay.bind("<F1>", lambda e: self.hide())
        self._overlay.bind("<Key>", self._on_key)

        self._overlay.protocol("WM_DELETE_WINDOW", self.hide)

    def _build_shortcut_list(self, filter_text=""):
        for w in self._content_frame.winfo_children():
            w.destroy()

        theme = self.theme
        ft = filter_text.lower().strip()

        canvas = tk.Canvas(self._content_frame, bg="#11111b",
                           bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._content_frame, orient=tk.VERTICAL,
                                  command=canvas.yview)
        inner = tk.Frame(canvas, bg="#11111b")

        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        col_frame = tk.Frame(inner, bg="#11111b")
        col_frame.pack(fill=tk.BOTH, expand=True)

        categories = []
        for cat_name, shortcuts in _SHORTCUTS:
            if ft:
                filtered = [(desc, key) for desc, key in shortcuts
                            if ft in desc.lower() or ft in key.lower()]
                if not filtered:
                    continue
                categories.append((cat_name, filtered))
            else:
                categories.append((cat_name, shortcuts))

        if not categories:
            tk.Label(col_frame, text="No shortcuts match your search.",
                     bg="#11111b",
                     fg=theme.get_color("text", "secondary"),
                     font=("Segoe UI", 10)).pack(pady=40)
            return

        num_cols = 2 if len(categories) > 3 else 1
        col_frame.columnconfigure(list(range(num_cols)), weight=1)

        for idx, (cat_name, shortcuts) in enumerate(categories):
            col = idx % num_cols
            row_idx = idx // num_cols

            cat_frame = tk.Frame(col_frame, bg="#11111b")
            cat_frame.grid(row=row_idx, column=col, sticky="nsew",
                           padx=(0, 24 if num_cols > 1 else 0), pady=(0, 12))

            tk.Label(cat_frame, text=cat_name.upper(),
                     bg="#11111b",
                     fg=theme.get_color("accent", "bg"),
                     font=("Segoe UI", 9, "bold"),
                     anchor="w").pack(fill=tk.X, pady=(0, 4))

            for desc, key in shortcuts:
                row = tk.Frame(cat_frame, bg="#11111b", height=22)
                row.pack(fill=tk.X, pady=1)
                row.pack_propagate(False)

                tk.Label(row, text=desc,
                         bg="#11111b",
                         fg=theme.get_color("text", "primary"),
                         font=("Segoe UI", 8),
                         anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

                key_frame = tk.Frame(row, bg=theme.get_color("surface", "bg"),
                                     bd=0)
                key_frame.pack(side=tk.RIGHT)

                tk.Label(key_frame, text=key,
                         bg=theme.get_color("surface", "bg"),
                         fg=theme.get_color("text", "secondary"),
                         font=("Consolas", 8),
                         padx=6, pady=1).pack()

        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _filter_shortcuts(self):
        if self._search_var:
            self._build_shortcut_list(self._search_var.get())

    def _on_key(self, event):
        if event.keysym == "Escape":
            self.hide()
        elif event.keysym == "F1":
            self.hide()
