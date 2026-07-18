import tkinter as tk
from tkinter import ttk

try:
    import customtkinter as ctk
except Exception:
    ctk = None

from ui.theme_manager import ThemeManager


_TAB_ICONS = {
    "bookmarks": "\U0001f519",
    "thumbnails": "\U0001f5bc",
    "search": "\U0001f50d",
}


class NavigationPanel:
    def __init__(self, editor, parent):
        self.editor = editor
        self.parent = parent
        self.theme = ThemeManager
        self._active_tab = "thumbnails"

        self.frame = tk.Frame(parent, bg=self.theme.get_color("panel", "bg"),
                              bd=0, highlightthickness=0)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self._tab_bar = tk.Frame(self.frame, bg=self.theme.get_color("panel", "bg"), bd=0)
        self._tab_bar.pack(fill=tk.X, padx=2, pady=(2, 0))

        self._tab_buttons = {}
        self._tab_contents = {}
        self._search_var = None
        self._search_results_frame = None
        self._bookmark_tree = None

        self._build_tabs()
        self._build_bookmarks_tab()
        self._build_thumbnails_tab()
        self._build_search_tab()
        self._switch_tab("thumbnails")

    def _build_tabs(self):
        theme = self.theme
        for name, icon in _TAB_ICONS.items():
            btn = tk.Button(self._tab_bar, text=icon,
                            bg=theme.get_color("panel", "bg"),
                            fg=theme.get_color("text", "secondary"),
                            font=("Segoe UI", 12),
                            relief="flat", bd=0, padx=8, pady=3,
                            cursor="hand2",
                            command=lambda n=name: self._switch_tab(n))
            btn.pack(side=tk.LEFT, padx=1)
            btn.bind("<Enter>",
                     lambda e, b=btn: b.configure(fg=theme.get_color("text", "primary"))
                     if self._active_tab != name else None)
            btn.bind("<Leave>",
                     lambda e, b=btn, n=name: b.configure(
                         fg=theme.get_color("accent", "bg") if self._active_tab == n
                         else theme.get_color("text", "secondary")))
            self._tab_buttons[name] = btn

        sep = tk.Frame(self._tab_bar, bg=theme.get_color("separator", ""), height=1)
        sep.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(2, 0))

    def _switch_tab(self, name):
        theme = self.theme
        self._active_tab = name
        for tname, btn in self._tab_buttons.items():
            if tname == name:
                btn.configure(bg=theme.get_color("accent", "bg"),
                              fg=theme.get_color("bg", ""))
            else:
                btn.configure(bg=theme.get_color("panel", "bg"),
                              fg=theme.get_color("text", "secondary"))
        for tname, content in self._tab_contents.items():
            if tname == name:
                content.pack(fill=tk.BOTH, expand=True)
            else:
                content.pack_forget()

        if name == "bookmarks":
            self._refresh_bookmarks()
        elif name == "thumbnails":
            self._refresh_thumbnails()

    def _build_bookmarks_tab(self):
        theme = self.theme
        container = tk.Frame(self.frame, bg=theme.get_color("panel", "bg"))
        self._tab_contents["bookmarks"] = container

        header = tk.Frame(container, bg=theme.get_color("panel", "bg"))
        header.pack(fill=tk.X, padx=4, pady=(4, 2))
        tk.Label(header, text="Bookmarks",
                 bg=theme.get_color("panel", "bg"),
                 fg=theme.get_color("text", "primary"),
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=4)

        btn_frame = tk.Frame(header, bg=theme.get_color("panel", "bg"))
        btn_frame.pack(side=tk.RIGHT)

        add_btn = tk.Button(btn_frame, text="+",
                            bg=theme.get_color("button_bg", ""),
                            fg=theme.get_color("button_fg", ""),
                            font=("Segoe UI", 9), relief="flat", bd=0,
                            width=2, cursor="hand2",
                            command=self._add_bookmark)
        add_btn.pack(side=tk.LEFT, padx=1)

        del_btn = tk.Button(btn_frame, text="\u2212",
                            bg=theme.get_color("button_bg", ""),
                            fg=theme.get_color("button_fg", ""),
                            font=("Segoe UI", 9), relief="flat", bd=0,
                            width=2, cursor="hand2",
                            command=self._delete_bookmark)
        del_btn.pack(side=tk.LEFT, padx=1)

        tree_frame = tk.Frame(container, bg=theme.get_color("panel", "bg"))
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)

        style = ttk.Style()
        style.configure("Bookmark.Treeview",
                        background=theme.get_color("surface", "bg"),
                        foreground=theme.get_color("text", "primary"),
                        fieldbackground=theme.get_color("surface", "bg"),
                        font=("Segoe UI", 8),
                        borderwidth=0)
        style.configure("Bookmark.Treeview.Heading",
                        background=theme.get_color("panel", "bg"),
                        foreground=theme.get_color("text", "primary"),
                        font=("Segoe UI", 8, "bold"))
        style.map("Bookmark.Treeview",
                  background=[("selected", theme.get_color("accent", "bg"))],
                  foreground=[("selected", theme.get_color("bg", ""))])

        self._bookmark_tree = ttk.Treeview(tree_frame, columns=("page",),
                                           selectmode="browse",
                                           style="Bookmark.Treeview",
                                           show="tree headings")
        self._bookmark_tree.heading("#0", text="Bookmark")
        self._bookmark_tree.heading("page", text="Page")
        self._bookmark_tree.column("#0", width=120)
        self._bookmark_tree.column("page", width=45, anchor="center")

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                               command=self._bookmark_tree.yview)
        self._bookmark_tree.configure(yscrollcommand=scroll.set)
        self._bookmark_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._bookmark_tree.bind("<Double-1>", self._on_bookmark_activate)

    def _refresh_bookmarks(self):
        if not self._bookmark_tree:
            return
        for item in self._bookmark_tree.get_children():
            self._bookmark_tree.delete(item)
        if self.editor.total_pages > 0:
            for i in range(self.editor.total_pages):
                self._bookmark_tree.insert("", "end",
                                           text=f"Page {i + 1}",
                                           values=(i + 1,),
                                           open=True)

    def _on_bookmark_activate(self, event):
        sel = self._bookmark_tree.selection()
        if not sel:
            return
        vals = self._bookmark_tree.item(sel[0], "values")
        if vals:
            try:
                page_num = int(vals[0]) - 1
                self.editor.goto_page(page_num)
            except (ValueError, IndexError):
                pass

    def _add_bookmark(self):
        page = self.editor.current_page + 1
        name = f"Bookmark (Page {page})"
        if self._bookmark_tree:
            self._bookmark_tree.insert("", "end", text=name,
                                       values=(page,), open=True)

    def _delete_bookmark(self):
        if self._bookmark_tree:
            sel = self._bookmark_tree.selection()
            if sel:
                self._bookmark_tree.delete(sel[0])

    def _build_thumbnails_tab(self):
        theme = self.theme
        container = tk.Frame(self.frame, bg=theme.get_color("panel", "bg"))
        self._tab_contents["thumbnails"] = container

        self._thumb_canvas = tk.Canvas(container,
                                       bg=theme.get_color("panel", "bg"),
                                       bd=0, highlightthickness=0)
        self._thumb_scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL,
                                              command=self._thumb_canvas.yview)
        self._thumb_inner = tk.Frame(self._thumb_canvas,
                                     bg=theme.get_color("panel", "bg"))

        self._thumb_inner.bind("<Configure>",
                               lambda e: self._thumb_canvas.configure(
                                   scrollregion=self._thumb_canvas.bbox("all")))
        self._thumb_canvas.create_window((0, 0), window=self._thumb_inner,
                                         anchor="nw")
        self._thumb_canvas.configure(yscrollcommand=self._thumb_scrollbar.set)
        self._thumb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._thumb_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._thumb_canvas.bind("<MouseWheel>", self._on_thumb_mousewheel)

    def _on_thumb_mousewheel(self, event):
        self._thumb_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _refresh_thumbnails(self):
        for widget in self._thumb_inner.winfo_children():
            widget.destroy()

        theme = self.theme
        total = self.editor.total_pages
        if total == 0:
            tk.Label(self._thumb_inner, text="No pages",
                     bg=theme.get_color("panel", "bg"),
                     fg=theme.get_color("text", "secondary"),
                     font=("Segoe UI", 9)).pack(pady=30)
            return

        for i in range(total):
            self._create_thumb(i)

    def _create_thumb(self, page_index):
        theme = self.theme
        is_current = page_index == self.editor.current_page
        border_color = theme.get_color("accent", "bg") if is_current else theme.get_color("surface", "border")

        outer = tk.Frame(self._thumb_inner, bg=border_color, bd=0, padx=2, pady=2)
        outer.pack(fill=tk.X, padx=6, pady=3)

        inner = tk.Frame(outer, bg=theme.get_color("surface", "bg"), bd=0,
                         cursor="hand2")
        inner.pack(fill=tk.BOTH, expand=True)

        cw, ch = 96, 132
        preview = tk.Canvas(inner, width=cw, height=ch,
                            bg="#f8f9fa", bd=0, highlightthickness=0)
        preview.pack(padx=4, pady=4)

        preview.create_text(cw // 2, ch // 2,
                            text=f"P{page_index + 1}",
                            fill="#666666",
                            font=("Segoe UI", 14, "bold"),
                            anchor="center")

        page_label = tk.Label(inner, text=f"Page {page_index + 1}",
                              bg=theme.get_color("surface", "bg"),
                              fg=theme.get_color("text", "primary"),
                              font=("Segoe UI", 7))
        page_label.pack(pady=(0, 3))

        for w in [preview, inner, page_label, outer]:
            w.bind("<Button-1>",
                   lambda e, idx=page_index: self._on_thumb_click(idx))
            w.bind("<Button-3>",
                   lambda e, idx=page_index: self._on_thumb_context(e, idx))

    def _on_thumb_click(self, page_index):
        self.editor.goto_page(page_index)
        self.refresh()

    def _on_thumb_context(self, event, page_index):
        theme = self.theme
        menu = tk.Menu(self._thumb_inner, tearoff=0,
                       bg=theme.get_color("menu_bg", ""),
                       fg=theme.get_color("text", "primary"),
                       activebackground=theme.get_color("accent", "bg"),
                       activeforeground=theme.get_color("bg", ""),
                       font=("Segoe UI", 9))

        menu.add_command(label="Go to Page",
                         command=lambda: self.editor.goto_page(page_index))
        menu.add_separator()
        menu.add_command(label="Insert Page Before",
                         command=lambda: self.editor.page_service.add_page(page_index))
        menu.add_command(label="Insert Page After",
                         command=lambda: self.editor.page_service.add_page(page_index + 1))
        menu.add_separator()
        menu.add_command(label="Delete Page",
                         command=lambda: self.editor.page_service.delete_page(page_index))
        menu.add_command(label="Duplicate Page",
                         command=lambda: self.editor.page_service.duplicate_page(page_index))
        menu.add_separator()
        menu.add_command(label="Rotate CW",
                         command=lambda: self.editor.page_service.rotate_page(page_index, 90))
        menu.add_command(label="Rotate CCW",
                         command=lambda: self.editor.page_service.rotate_page(page_index, -90))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _build_search_tab(self):
        theme = self.theme
        container = tk.Frame(self.frame, bg=theme.get_color("panel", "bg"))
        self._tab_contents["search"] = container

        search_frame = tk.Frame(container, bg=theme.get_color("panel", "bg"))
        search_frame.pack(fill=tk.X, padx=4, pady=4)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._on_search_input())

        search_entry = tk.Entry(search_frame, textvariable=self._search_var,
                                bg=theme.get_color("entry_bg", ""),
                                fg=theme.get_color("text", "primary"),
                                insertbackground=theme.get_color("text", "primary"),
                                font=("Segoe UI", 9),
                                relief="flat", bd=0,
                                highlightthickness=1,
                                highlightbackground=theme.get_color("surface", "border"),
                                highlightcolor=theme.get_color("accent", "bg"))
        search_entry.pack(fill=tk.X, ipady=3)
        search_entry.bind("<Return>", lambda e: self._do_search())

        search_btn = tk.Button(search_frame, text="\U0001f50d Search",
                               bg=theme.get_color("accent", "bg"),
                               fg=theme.get_color("bg", ""),
                               font=("Segoe UI", 8, "bold"),
                               relief="flat", bd=0, padx=8, pady=3,
                               cursor="hand2",
                               command=self._do_search)
        search_btn.pack(fill=tk.X, pady=(4, 0))

        self._search_results_frame = tk.Frame(container,
                                              bg=theme.get_color("panel", "bg"))
        self._search_results_frame.pack(fill=tk.BOTH, expand=True, padx=4)

        tk.Label(self._search_results_frame,
                 text="Type to search across all elements",
                 bg=theme.get_color("panel", "bg"),
                 fg=theme.get_color("text", "secondary"),
                 font=("Segoe UI", 8)).pack(pady=20)

    def _on_search_input(self):
        pass

    def _do_search(self):
        if not self._search_results_frame or not self._search_var:
            return
        theme = self.theme
        for w in self._search_results_frame.winfo_children():
            w.destroy()

        query = self._search_var.get().strip().lower()
        if not query:
            tk.Label(self._search_results_frame,
                     text="Type to search across all elements",
                     bg=theme.get_color("panel", "bg"),
                     fg=theme.get_color("text", "secondary"),
                     font=("Segoe UI", 8)).pack(pady=20)
            return

        results = []
        for i, elem in enumerate(self.editor.elements):
            text = getattr(elem, "text", "") or getattr(elem, "url", "") or getattr(elem, "label", "") or getattr(elem, "field_name", "")
            if query in text.lower():
                results.append((i, elem, text))

        if not results:
            tk.Label(self._search_results_frame,
                     text="No results found",
                     bg=theme.get_color("panel", "bg"),
                     fg=theme.get_color("text", "secondary"),
                     font=("Segoe UI", 9)).pack(pady=20)
            return

        for elem_idx, elem, text in results:
            item = tk.Frame(self._search_results_frame,
                            bg=theme.get_color("surface", "bg"),
                            bd=0, cursor="hand2")
            item.pack(fill=tk.X, pady=1)

            preview = text[:40] + ("..." if len(text) > 40 else "")
            page_num = getattr(elem, "page", 0) + 1
            etype = getattr(elem, "type_name", type(elem).__name__)

            content = tk.Frame(item, bg=theme.get_color("surface", "bg"))
            content.pack(fill=tk.X, padx=6, pady=4)

            tk.Label(content, text=etype.title(),
                     bg=theme.get_color("surface", "bg"),
                     fg=theme.get_color("accent", "bg"),
                     font=("Segoe UI", 7, "bold"),
                     anchor="w").pack(anchor="w")

            tk.Label(content, text=preview,
                     bg=theme.get_color("surface", "bg"),
                     fg=theme.get_color("text", "primary"),
                     font=("Segoe UI", 8),
                     anchor="w").pack(anchor="w")

            tk.Label(content, text=f"Page {page_num}",
                     bg=theme.get_color("surface", "bg"),
                     fg=theme.get_color("text", "secondary"),
                     font=("Segoe UI", 7),
                     anchor="e").pack(anchor="e")

            for w in [item, content]:
                w.bind("<Button-1>",
                       lambda e, idx=elem_idx: self._on_result_click(idx))
                w.bind("<Enter>",
                       lambda e, f=item: f.configure(
                           bg=theme.get_color("hover_bg", "")))
                w.bind("<Leave>",
                       lambda e, f=item: f.configure(
                           bg=theme.get_color("surface", "bg")))

    def _on_result_click(self, elem_idx):
        self.editor.selected_element = elem_idx
        elem = self.editor.elements[elem_idx]
        page = getattr(elem, "page", 0)
        if page != self.editor.current_page:
            self.editor.goto_page(page)
        self.editor.canvas_manager.update_preview()

    def refresh(self):
        self._switch_tab(self._active_tab)
