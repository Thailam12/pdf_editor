import tkinter as tk
from tkinter import ttk, messagebox

try:
    import customtkinter as ctk
except Exception:
    ctk = None

BG = "#1e1e2e"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
BTN_BG = "#45475a"
THUMB_BG = "#313244"
ACTIVE_BG = "#585b70"


class PagePanel:
    def __init__(self, editor, parent):
        self.editor = editor
        self.parent = parent
        self.frame = tk.Frame(parent, bg=BG, bd=0, highlightthickness=0)
        self.frame.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(self.frame, bg=BG, bd=0)
        header.pack(fill=tk.X, padx=4, pady=(4, 2))
        tk.Label(header, text="Pages", bg=BG, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=4)

        self.canvas = tk.Canvas(self.frame, bg=BG, bd=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.inner_frame = tk.Frame(self.canvas, bg=BG)

        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        self._thumbnails = []
        self._drag_data = {"index": None, "widget": None}

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self._thumbnails.clear()

        total = self.editor.total_pages
        if total == 0:
            tk.Label(self.inner_frame, text="No pages", bg=BG, fg="#a6adc8",
                     font=("Segoe UI", 9)).pack(pady=20)
            return

        for i in range(total):
            thumb_frame = self._create_thumbnail(i)
            self._thumbnails.append(thumb_frame)

    def _create_thumbnail(self, page_index):
        is_current = page_index == self.editor.current_page
        border_color = ACCENT if is_current else BTN_BG

        outer = tk.Frame(self.inner_frame, bg=border_color, bd=0, padx=2, pady=2)
        outer.pack(fill=tk.X, padx=6, pady=3)

        inner = tk.Frame(outer, bg=THUMB_BG, bd=0, cursor="hand2")
        inner.pack(fill=tk.BOTH, expand=True)

        canvas_w, canvas_h = 100, 140
        preview = tk.Canvas(inner, width=canvas_w, height=canvas_h,
                            bg="#f8f9fa", bd=0, highlightthickness=0)
        preview.pack(padx=4, pady=4)

        preview.create_text(canvas_w // 2, canvas_h // 2,
                            text=f"P{page_index + 1}",
                            fill="#666666",
                            font=("Segoe UI", 16, "bold"),
                            anchor="center")

        page_label = tk.Label(inner, text=f"Page {page_index + 1}",
                              bg=THUMB_BG, fg=FG, font=("Segoe UI", 8))
        page_label.pack(pady=(0, 4))

        preview.bind("<Button-1>", lambda e, idx=page_index: self._on_click(idx))
        preview.bind("<Double-Button-1>", lambda e, idx=page_index: self._on_double_click(idx))
        inner.bind("<Button-1>", lambda e, idx=page_index: self._on_click(idx))
        page_label.bind("<Button-1>", lambda e, idx=page_index: self._on_click(idx))

        outer.bind("<Button-3>", lambda e, idx=page_index: self._show_context_menu(e, idx))
        inner.bind("<Button-3>", lambda e, idx=page_index: self._show_context_menu(e, idx))
        preview.bind("<Button-3>", lambda e, idx=page_index: self._show_context_menu(e, idx))
        page_label.bind("<Button-3>", lambda e, idx=page_index: self._show_context_menu(e, idx))

        preview.bind("<ButtonPress-1>", lambda e, idx=page_index: self._start_drag(e, idx))
        preview.bind("<B1-Motion>", self._on_drag)
        preview.bind("<ButtonRelease-1>", self._end_drag)

        if is_current:
            outer.configure(bg=ACCENT)

        return outer

    def _on_click(self, page_index):
        if self.editor.current_page != page_index:
            self.editor.current_page = page_index
            self.editor.selected_element = None
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.refresh()

    def _on_double_click(self, page_index):
        self._on_click(page_index)

    def _start_drag(self, event, page_index):
        self._drag_data["index"] = page_index
        self._drag_data["start_y"] = event.y_root

    def _on_drag(self, event):
        pass

    def _end_drag(self, event):
        if self._drag_data["index"] is None:
            return
        start_y = self._drag_data.get("start_y", 0)
        delta = event.y_root - start_y
        if abs(delta) > 50:
            direction = 1 if delta > 0 else -1
            old_idx = self._drag_data["index"]
            new_idx = old_idx + direction
            if 0 <= new_idx < self.editor.total_pages:
                self._swap_pages(old_idx, new_idx)
        self._drag_data = {"index": None, "widget": None}

    def _swap_pages(self, idx1, idx2):
        self.editor.undo_manager.save_state(self.editor.elements)
        for elem in self.editor.elements:
            if elem.page == idx1:
                elem.page = idx2
            elif elem.page == idx2:
                elem.page = idx1
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.refresh()

    def _show_context_menu(self, event, page_index):
        menu = tk.Menu(self.inner_frame, tearoff=0,
                       bg=BG, fg=FG,
                       activebackground=ACCENT, activeforeground=BG,
                       font=("Segoe UI", 9))
        menu.add_command(label="Insert Page Before",
                         command=lambda: self._insert_page(page_index))
        menu.add_command(label="Insert Page After",
                         command=lambda: self._insert_page(page_index + 1))
        menu.add_separator()
        menu.add_command(label="Move Up",
                         command=lambda: self._move_page(page_index, -1))
        menu.add_command(label="Move Down",
                         command=lambda: self._move_page(page_index, 1))
        menu.add_separator()
        menu.add_command(label="Duplicate",
                         command=lambda: self._duplicate_page(page_index))
        menu.add_command(label="Rotate CW",
                         command=lambda: self._rotate_page(page_index, 90))
        menu.add_command(label="Rotate CCW",
                         command=lambda: self._rotate_page(page_index, -90))
        menu.add_separator()
        menu.add_command(label="Delete Page",
                         command=lambda: self._delete_page(page_index))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _insert_page(self, at_index):
        self.editor.undo_manager.save_state(self.editor.elements)
        for elem in self.editor.elements:
            if elem.page >= at_index:
                elem.page += 1
        self.editor.total_pages += 1
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.refresh()

    def _move_page(self, page_index, direction):
        new_index = page_index + direction
        if new_index < 0 or new_index >= self.editor.total_pages:
            return
        self.editor.undo_manager.save_state(self.editor.elements)
        for elem in self.editor.elements:
            if elem.page == page_index:
                elem.page = new_index
            elif elem.page == new_index:
                elem.page = page_index
        if self.editor.current_page == page_index:
            self.editor.current_page = new_index
        elif self.editor.current_page == new_index:
            self.editor.current_page = page_index
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.refresh()

    def _duplicate_page(self, page_index):
        self.editor.undo_manager.save_state(self.editor.elements)
        new_index = self.editor.total_pages
        self.editor.total_pages += 1
        elems_to_copy = [e for e in self.editor.elements if e.page == page_index]
        import copy
        for elem in elems_to_copy:
            new_elem = copy.deepcopy(elem)
            new_elem.page = new_index
            self.editor.elements.append(new_elem)
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.refresh()

    def _rotate_page(self, page_index, angle):
        self.editor.undo_manager.save_state(self.editor.elements)
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.refresh()

    def _delete_page(self, page_index):
        if self.editor.total_pages <= 1:
            messagebox.showwarning("Warning", "Cannot delete the last page.")
            return
        if not messagebox.askyesno("Confirm", f"Delete page {page_index + 1}?"):
            return
        self.editor.undo_manager.save_state(self.editor.elements)
        self.editor.elements = [e for e in self.editor.elements if e.page != page_index]
        for elem in self.editor.elements:
            if elem.page > page_index:
                elem.page -= 1
        self.editor.total_pages -= 1
        if self.editor.current_page >= self.editor.total_pages:
            self.editor.current_page = max(0, self.editor.total_pages - 1)
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.refresh()
