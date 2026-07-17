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
ITEM_BG = "#313244"
ACTIVE_BG = "#585b70"

_TYPE_ICONS = {
    "text": "\U0001f520",
    "image": "\U0001f5bc",
    "shape": "\u2b21",
    "line": "\u2571",
    "highlight": "\U0001f4dd",
    "annotation": "\u270d",
    "note": "\U0001f4ac",
    "stamp": "\U0001f4ac",
    "signature": "\u270d",
    "freehand": "\u270d",
    "link": "\U0001f517",
    "redact": "\u2b1a",
    "watermark": "\u2602",
    "formfield": "\U0001f4dd",
    "headerfooter": "\U0001f4c4",
    "attachment": "\U0001f4ce",
}


class LayersPanel:
    def __init__(self, editor, parent):
        self.editor = editor
        self.parent = parent
        self.frame = tk.Frame(parent, bg=BG, bd=0, highlightthickness=0)
        self.frame.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(self.frame, bg=BG, bd=0)
        header.pack(fill=tk.X, padx=4, pady=(4, 2))
        tk.Label(header, text="Layers", bg=BG, fg=FG,
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

        self._items = []
        self._selected_idx = None

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self._items.clear()

        current_page = self.editor.current_page
        page_elements = [
            (i, e) for i, e in enumerate(self.editor.elements)
            if getattr(e, "page", 0) == current_page
        ]

        if not page_elements:
            tk.Label(self.inner_frame, text="No elements", bg=BG, fg="#a6adc8",
                     font=("Segoe UI", 9)).pack(pady=20)
            return

        for idx, elem in reversed(list(enumerate(page_elements))):
            orig_idx, elem_obj = page_elements[idx]
            self._create_layer_item(orig_idx, elem_obj, idx)

    def _create_layer_item(self, orig_index, elem, display_index):
        is_selected = (self.editor.selected_element == orig_index)
        bg_color = ACCENT if is_selected else ITEM_BG

        item_frame = tk.Frame(self.inner_frame, bg=bg_color, bd=0, cursor="hand2")
        item_frame.pack(fill=tk.X, padx=4, pady=2)

        content = tk.Frame(item_frame, bg=bg_color, bd=0)
        content.pack(fill=tk.X, padx=4, pady=3)

        type_icon = _TYPE_ICONS.get(getattr(elem, "type_name", ""), "\u2753")
        icon_label = tk.Label(content, text=type_icon, bg=bg_color, fg=FG,
                              font=("Segoe UI", 12), width=2)
        icon_label.pack(side=tk.LEFT, padx=(0, 4))

        elem_type = getattr(elem, "type_name", type(elem).__name__)
        preview_text = self._get_preview_text(elem)
        name_text = f"{elem_type.title()}"
        if preview_text:
            name_text += f": {preview_text}"

        name_label = tk.Label(content, text=name_text, bg=bg_color, fg=FG,
                              font=("Segoe UI", 8), anchor="w", wraplength=150,
                              justify="left")
        name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        vis = getattr(elem, "visible", True)
        eye_text = "\U0001f441" if vis else "\U0001f441\u200d\U0001f5e8"
        eye_btn = tk.Button(content, text=eye_text, bg=bg_color, fg=FG,
                            font=("Segoe UI", 10), relief="flat", bd=0,
                            cursor="hand2", width=2,
                            command=lambda i=orig_index: self._toggle_visibility(i))
        eye_btn.pack(side=tk.RIGHT, padx=2)

        for widget in [item_frame, content, icon_label, name_label, eye_btn]:
            widget.bind("<Button-1>", lambda e, i=orig_index: self._on_select(i))
            widget.bind("<Double-Button-1>", lambda e, i=orig_index: self._on_select(i))
            widget.bind("<Button-3>", lambda e, i=orig_index: self._show_context_menu(e, i))

    def _get_preview_text(self, elem):
        if hasattr(elem, "text") and elem.text:
            text = elem.text
            return text[:20] + "..." if len(text) > 20 else text
        if hasattr(elem, "url") and elem.url:
            return elem.url[:20]
        if hasattr(elem, "shape_type"):
            return elem.shape_type
        if hasattr(elem, "path") and elem.path:
            import os
            return os.path.basename(elem.path)[:20]
        if hasattr(elem, "field_name") and elem.field_name:
            return elem.field_name
        return ""

    def _on_select(self, orig_index):
        self.editor.selected_element = orig_index
        self.editor.update_info_panel()
        self.refresh()

    def _toggle_visibility(self, orig_index):
        elem = self.editor.elements[orig_index]
        elem.visible = not getattr(elem, "visible", True)
        self.editor.canvas_manager.update_preview()
        self.refresh()

    def _show_context_menu(self, event, orig_index):
        menu = tk.Menu(self.inner_frame, tearoff=0,
                       bg=BG, fg=FG,
                       activebackground=ACCENT, activeforeground=BG,
                       font=("Segoe UI", 9))

        menu.add_command(label="Edit",
                         command=lambda: self._edit_element(orig_index))
        menu.add_separator()
        menu.add_command(label="Move Up",
                         command=lambda: self._move_element(orig_index, -1))
        menu.add_command(label="Move Down",
                         command=lambda: self._move_element(orig_index, 1))
        menu.add_separator()
        menu.add_command(label="Bring to Front",
                         command=lambda: self._bring_to_front(orig_index))
        menu.add_command(label="Send to Back",
                         command=lambda: self._send_to_back(orig_index))
        menu.add_separator()
        menu.add_command(label="Delete",
                         command=lambda: self._delete_element(orig_index))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _edit_element(self, orig_index):
        self.editor.selected_element = orig_index
        self.editor.edit_selected_element()

    def _delete_element(self, orig_index):
        if not messagebox.askyesno("Confirm", "Delete this element?"):
            return
        self.editor.undo_manager.save_state(self.editor.elements)
        del self.editor.elements[orig_index]
        if self.editor.selected_element == orig_index:
            self.editor.selected_element = None
        elif self.editor.selected_element is not None and self.editor.selected_element > orig_index:
            self.editor.selected_element -= 1
        self.editor.element_images.clear()
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.refresh()

    def _move_element(self, orig_index, direction):
        new_index = orig_index + direction
        if new_index < 0 or new_index >= len(self.editor.elements):
            return
        self.editor.undo_manager.save_state(self.editor.elements)
        self.editor.elements[orig_index], self.editor.elements[new_index] = \
            self.editor.elements[new_index], self.editor.elements[orig_index]
        if self.editor.selected_element == orig_index:
            self.editor.selected_element = new_index
        elif self.editor.selected_element == new_index:
            self.editor.selected_element = orig_index
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.refresh()

    def _bring_to_front(self, orig_index):
        if orig_index >= len(self.editor.elements) - 1:
            return
        self.editor.undo_manager.save_state(self.editor.elements)
        elem = self.editor.elements.pop(orig_index)
        self.editor.elements.append(elem)
        if self.editor.selected_element == orig_index:
            self.editor.selected_element = len(self.editor.elements) - 1
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.refresh()

    def _send_to_back(self, orig_index):
        if orig_index <= 0:
            return
        self.editor.undo_manager.save_state(self.editor.elements)
        elem = self.editor.elements.pop(orig_index)
        self.editor.elements.insert(0, elem)
        if self.editor.selected_element == orig_index:
            self.editor.selected_element = 0
        self.editor.canvas_manager.update_preview()
        self.editor.update_info_panel()
        self.refresh()
