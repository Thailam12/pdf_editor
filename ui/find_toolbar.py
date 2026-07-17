import tkinter as tk
from tkinter import ttk
import re

try:
    import customtkinter as ctk
except Exception:
    ctk = None

from ui.theme_manager import ThemeManager


class FindToolbar:
    def __init__(self, editor):
        self.editor = editor
        self.theme = ThemeManager
        self._frame = None
        self._visible = False
        self._search_var = None
        self._match_case_var = None
        self._whole_word_var = None
        self._regex_var = None
        self._status_label = None
        self._matches = []
        self._current_index = -1

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def show(self):
        if self._visible:
            self._entry_focus()
            return
        self._visible = True
        self._build()

    def hide(self):
        if not self._visible:
            return
        self._visible = False
        self._clear_highlights()
        if self._frame:
            self._frame.destroy()
            self._frame = None

    def _entry_focus(self):
        if self._frame:
            for w in self._frame.winfo_children():
                if isinstance(w, tk.Frame):
                    for c in w.winfo_children():
                        if isinstance(c, tk.Entry):
                            c.focus_set()
                            c.select_range(0, tk.END)
                            return

    def _build(self):
        theme = self.theme
        canvas_frame = None
        for child in self.editor.root.winfo_children():
            if isinstance(child, tk.Frame):
                for c in child.winfo_children():
                    if hasattr(c, '__class__') and c.__class__.__name__ == 'Canvas':
                        canvas_frame = child.master
                        break
            if canvas_frame:
                break

        self._frame = tk.Frame(self.editor.root,
                               bg=theme.get_color("surface", "bg"),
                               bd=0, highlightthickness=1,
                               highlightbackground=theme.get_color("surface", "border"))
        self._frame.pack(side=tk.TOP, fill=tk.X, before=self.editor.ribbon
                         if hasattr(self.editor, 'ribbon') else None)

        inner = tk.Frame(self._frame, bg=theme.get_color("surface", "bg"))
        inner.pack(fill=tk.X, padx=6, pady=4)

        search_icon = tk.Label(inner, text="\U0001f50d",
                               bg=theme.get_color("surface", "bg"),
                               fg=theme.get_color("text", "secondary"),
                               font=("Segoe UI", 10))
        search_icon.pack(side=tk.LEFT, padx=(0, 4))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._do_search())

        search_entry = tk.Entry(inner, textvariable=self._search_var,
                                bg=theme.get_color("bg", ""),
                                fg=theme.get_color("text", "primary"),
                                insertbackground=theme.get_color("text", "primary"),
                                font=("Segoe UI", 10),
                                relief="flat", bd=0,
                                highlightthickness=2,
                                highlightbackground=theme.get_color("surface", "border"),
                                highlightcolor=theme.get_color("accent", "bg"))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3, padx=(0, 8))
        search_entry.focus_set()
        search_entry.bind("<Return>", lambda e: self._goto_next())
        search_entry.bind("<Shift-Return>", lambda e: self._goto_prev())
        search_entry.bind("<Escape>", lambda e: self.hide())

        self._status_label = tk.Label(inner, text="No results",
                                      bg=theme.get_color("surface", "bg"),
                                      fg=theme.get_color("text", "secondary"),
                                      font=("Segoe UI", 9),
                                      padx=8)
        self._status_label.pack(side=tk.LEFT)

        def _make_nav_btn(text, command):
            btn = tk.Button(inner, text=text,
                            bg=theme.get_color("button_bg", ""),
                            fg=theme.get_color("button_fg", ""),
                            font=("Segoe UI", 9),
                            relief="flat", bd=0, padx=6, pady=2,
                            cursor="hand2", command=command)
            btn.bind("<Enter>",
                     lambda e: btn.configure(bg=theme.get_color("hover_bg", ""))
                     if btn["state"] != "disabled" else None)
            btn.bind("<Leave>",
                     lambda e: btn.configure(bg=theme.get_color("button_bg", ""))
                     if btn["state"] != "disabled" else None)
            return btn

        self._prev_btn = _make_nav_btn("\u25c0", self._goto_prev)
        self._prev_btn.pack(side=tk.LEFT, padx=1)

        self._next_btn = _make_nav_btn("\u25b6", self._goto_next)
        self._next_btn.pack(side=tk.LEFT, padx=1)

        sep = tk.Frame(inner, bg=theme.get_color("separator", ""),
                       width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        self._match_case_var = tk.BooleanVar(value=False)
        mc_btn = tk.Checkbutton(inner, text="Aa",
                                variable=self._match_case_var,
                                bg=theme.get_color("surface", "bg"),
                                fg=theme.get_color("text", "secondary"),
                                selectcolor=theme.get_color("surface", "bg"),
                                activebackground=theme.get_color("surface", "bg"),
                                activeforeground=theme.get_color("text", "primary"),
                                font=("Segoe UI", 8),
                                command=self._do_search)
        mc_btn.pack(side=tk.LEFT, padx=2)

        self._whole_word_var = tk.BooleanVar(value=False)
        ww_btn = tk.Checkbutton(inner, text="\u2343",
                                variable=self._whole_word_var,
                                bg=theme.get_color("surface", "bg"),
                                fg=theme.get_color("text", "secondary"),
                                selectcolor=theme.get_color("surface", "bg"),
                                activebackground=theme.get_color("surface", "bg"),
                                activeforeground=theme.get_color("text", "primary"),
                                font=("Segoe UI", 9),
                                command=self._do_search)
        ww_btn.pack(side=tk.LEFT, padx=2)

        self._regex_var = tk.BooleanVar(value=False)
        re_btn = tk.Checkbutton(inner, text=".*",
                                variable=self._regex_var,
                                bg=theme.get_color("surface", "bg"),
                                fg=theme.get_color("text", "secondary"),
                                selectcolor=theme.get_color("surface", "bg"),
                                activebackground=theme.get_color("surface", "bg"),
                                activeforeground=theme.get_color("text", "primary"),
                                font=("Segoe UI", 8),
                                command=self._do_search)
        re_btn.pack(side=tk.LEFT, padx=2)

        close_btn = tk.Button(inner, text="\u2715",
                              bg=theme.get_color("surface", "bg"),
                              fg=theme.get_color("text", "secondary"),
                              font=("Segoe UI", 10),
                              relief="flat", bd=0, padx=6,
                              cursor="hand2", command=self.hide)
        close_btn.pack(side=tk.RIGHT, padx=(8, 0))
        close_btn.bind("<Enter>",
                       lambda e: close_btn.configure(fg=theme.get_color("error", "fg")))
        close_btn.bind("<Leave>",
                       lambda e: close_btn.configure(fg=theme.get_color("text", "secondary")))

    def _do_search(self):
        self._clear_highlights()
        self._matches.clear()
        self._current_index = -1

        query = self._search_var.get() if self._search_var else ""
        if not query:
            self._update_status()
            return

        match_case = self._match_case_var.get() if self._match_case_var else False
        whole_word = self._whole_word_var.get() if self._whole_word_var else False
        use_regex = self._regex_var.get() if self._regex_var else False

        for i, elem in enumerate(self.editor.elements):
            if getattr(elem, "page", 0) != self.editor.current_page:
                continue
            text = getattr(elem, "text", "")
            if not text:
                continue

            try:
                if use_regex:
                    flags = 0 if match_case else re.IGNORECASE
                    pattern = re.compile(query, flags)
                    matches = list(pattern.finditer(text))
                    if matches:
                        self._matches.append((i, elem))
                else:
                    hay = text if match_case else text.lower()
                    needle = query if match_case else query.lower()

                    if whole_word:
                        words = hay.split()
                        found = any(w == needle for w in words)
                    else:
                        found = needle in hay

                    if found:
                        self._matches.append((i, elem))
            except re.error:
                self._matches.append((i, elem))

        if self._matches:
            self._current_index = 0

        self._highlight_matches()
        self._update_status()

    def _highlight_matches(self):
        if not hasattr(self.editor, 'canvas_preview'):
            return
        canvas = self.editor.canvas_preview
        canvas.delete("find_highlight")

        for idx, (elem_idx, elem) in enumerate(self._matches):
            bx, by, bw, bh = elem.get_bounds()
            zoom = self.editor.zoom_level / 100.0
            x1 = bx * zoom
            y1 = by * zoom
            x2 = (bx + bw) * zoom
            y2 = (by + bh) * zoom

            color = "#ff8c00" if idx == self._current_index else "#ffff00"
            alpha_color = color

            canvas.create_rectangle(x1 - 2, y1 - 2, x2 + 2, y2 + 2,
                                    outline=alpha_color, width=2,
                                    dash=(4, 2),
                                    tags="find_highlight")

    def _clear_highlights(self):
        if hasattr(self.editor, 'canvas_preview'):
            self.editor.canvas_preview.delete("find_highlight")

    def _goto_next(self):
        if not self._matches:
            return
        self._current_index = (self._current_index + 1) % len(self._matches)
        self._go_to_match()
        self._update_status()
        self._highlight_matches()

    def _goto_prev(self):
        if not self._matches:
            return
        self._current_index = (self._current_index - 1) % len(self._matches)
        self._go_to_match()
        self._update_status()
        self._highlight_matches()

    def _go_to_match(self):
        if self._current_index < 0 or self._current_index >= len(self._matches):
            return
        elem_idx, elem = self._matches[self._current_index]
        self.editor.selected_element = elem_idx
        self.editor.canvas_manager.update_preview()

    def _update_status(self):
        if not self._status_label:
            return
        total = len(self._matches)
        if total == 0:
            self._status_label.configure(text="No results")
        else:
            current = self._current_index + 1
            self._status_label.configure(text=f"{current} of {total}")

    def find_next(self):
        self._goto_next()

    def find_prev(self):
        self._goto_prev()
