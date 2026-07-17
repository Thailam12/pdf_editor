import tkinter as tk
import os

try:
    import customtkinter as ctk
except Exception:
    ctk = None

from ui.theme_manager import ThemeManager


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


class _ContextMenuItem:
    def __init__(self, label="", shortcut="", command=None, icon="",
                 enabled=True, submenu=None, separator=False):
        self.label = label
        self.shortcut = shortcut
        self.command = command
        self.icon = icon
        self.enabled = enabled
        self.submenu = submenu
        self.separator = separator


class ContextMenuManager:
    def __init__(self, editor):
        self.editor = editor
        self.theme = ThemeManager
        self._menu = None
        self._keyboard_index = 0

    def show_canvas_context_menu(self, event):
        items = self._get_canvas_menu_items()
        self._show_menu(event.x_root, event.y_root, items)

    def show_text_element_menu(self, event, elem_idx):
        items = self._get_text_element_menu(elem_idx)
        self._show_menu(event.x_root, event.y_root, items)

    def show_image_element_menu(self, event, elem_idx):
        items = self._get_image_element_menu(elem_idx)
        self._show_menu(event.x_root, event.y_root, items)

    def show_shape_element_menu(self, event, elem_idx):
        items = self._get_shape_element_menu(elem_idx)
        self._show_menu(event.x_root, event.y_root, items)

    def show_generic_element_menu(self, event, elem_idx):
        items = self._get_generic_element_menu(elem_idx)
        self._show_menu(event.x_root, event.y_root, items)

    def show_page_panel_menu(self, event, page_index):
        items = self._get_page_panel_menu(page_index)
        self._show_menu(event.x_root, event.y_root, items)

    def show_layer_panel_menu(self, event, elem_idx):
        items = self._get_layer_panel_menu(elem_idx)
        self._show_menu(event.x_root, event.y_root, items)

    def _get_canvas_menu_items(self):
        has_doc = self.editor.current_pdf is not None
        has_elem = self.editor.selected_element is not None
        has_clip = False
        try:
            clip = self.editor.root.clipboard_get()
            has_clip = bool(clip)
        except Exception:
            pass

        return [
            _ContextMenuItem(icon="\U0001f4ea", label="Paste",
                            shortcut="Ctrl+V",
                            command=self.editor.paste_clipboard,
                            enabled=has_clip),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\U0001f520", label="Insert Text",
                            command=lambda: self.editor.set_tool("text"),
                            enabled=has_doc),
            _ContextMenuItem(icon="\U0001f5bc", label="Insert Image",
                            command=getattr(self.editor, "add_image",
                                            self.editor.insert_image),
                            enabled=has_doc),
            _ContextMenuItem(icon="\u2b21", label="Insert Shape",
                            submenu=[
                                _ContextMenuItem(label="Rectangle",
                                                command=lambda: self.editor.set_tool("rect")),
                                _ContextMenuItem(label="Ellipse",
                                                command=lambda: self.editor.set_tool("ellipse")),
                                _ContextMenuItem(label="Triangle",
                                                command=lambda: self.editor.set_tool("triangle")),
                                _ContextMenuItem(label="Line",
                                                command=lambda: self.editor.set_tool("line")),
                                _ContextMenuItem(label="Arrow",
                                                command=lambda: self.editor.set_tool("arrow")),
                            ],
                            enabled=has_doc),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\u21b6", label="Undo",
                            shortcut="Ctrl+Z",
                            command=self.editor.undo),
            _ContextMenuItem(icon="\u21b7", label="Redo",
                            shortcut="Ctrl+Y",
                            command=self.editor.redo),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Select All",
                            shortcut="Ctrl+A",
                            command=self.editor.select_all,
                            enabled=has_doc),
            _ContextMenuItem(label="Deselect",
                            shortcut="Escape",
                            command=self.editor.deselect_all,
                            enabled=has_elem),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Page Properties",
                            enabled=has_doc),
            _ContextMenuItem(label="Fit Page",
                            command=self.editor.zoom_fit,
                            enabled=has_doc),
            _ContextMenuItem(label="Fit Width",
                            command=self.editor.zoom_width,
                            enabled=has_doc),
        ]

    def _get_text_element_menu(self, elem_idx):
        elem = self.editor.elements[elem_idx]
        return [
            _ContextMenuItem(icon="\u270f", label="Edit Text",
                            shortcut="Enter",
                            command=lambda: self._edit_element(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\u2702", label="Cut",
                            shortcut="Ctrl+X",
                            command=self.editor.cut_selected),
            _ContextMenuItem(icon="\U0001f4cb", label="Copy",
                            shortcut="Ctrl+C",
                            command=self.editor.copy_selected),
            _ContextMenuItem(icon="\U0001f4ea", label="Paste",
                            shortcut="Ctrl+V",
                            command=self.editor.paste_clipboard),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\U0001f3a8", label="Text Color",
                            command=self.editor.pick_color),
            _ContextMenuItem(icon="\U0001f520", label="Font Size",
                            submenu=[
                                _ContextMenuItem(label=str(s),
                                                command=lambda s=s: self._set_font_size(s))
                                for s in [8, 10, 12, 14, 18, 24, 36, 48, 72]
                            ]),
            _ContextMenuItem(label="Bold",
                            shortcut="Ctrl+B",
                            command=self.editor.toggle_bold),
            _ContextMenuItem(label="Italic",
                            shortcut="Ctrl+I",
                            command=self.editor.toggle_italic),
            _ContextMenuItem(label="Underline",
                            shortcut="Ctrl+U",
                            command=self.editor.toggle_underline),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Bring to Front",
                            command=lambda: self._bring_to_front(elem_idx)),
            _ContextMenuItem(label="Send to Back",
                            command=lambda: self._send_to_back(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\U0001f5d1", label="Delete",
                            shortcut="Delete",
                            command=self.editor.delete_selected_element),
        ]

    def _get_image_element_menu(self, elem_idx):
        elem = self.editor.elements[elem_idx]
        return [
            _ContextMenuItem(label="Edit Image",
                            command=lambda: self._edit_element(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\u2702", label="Cut",
                            shortcut="Ctrl+X",
                            command=self.editor.cut_selected),
            _ContextMenuItem(icon="\U0001f4cb", label="Copy",
                            shortcut="Ctrl+C",
                            command=self.editor.copy_selected),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Replace Image",
                            command=getattr(self.editor, "add_image",
                                            self.editor.insert_image)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Lock Position",
                            command=lambda: self._toggle_locked(elem_idx)),
            _ContextMenuItem(label="Bring to Front",
                            command=lambda: self._bring_to_front(elem_idx)),
            _ContextMenuItem(label="Send to Back",
                            command=lambda: self._send_to_back(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\U0001f5d1", label="Delete",
                            shortcut="Delete",
                            command=self.editor.delete_selected_element),
        ]

    def _get_shape_element_menu(self, elem_idx):
        elem = self.editor.elements[elem_idx]
        return [
            _ContextMenuItem(label="Edit Shape",
                            command=lambda: self._edit_element(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\U0001f3a8", label="Stroke Color",
                            command=self.editor.pick_color),
            _ContextMenuItem(label="Fill Color",
                            command=self.editor.pick_fill_color),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\u2702", label="Cut",
                            shortcut="Ctrl+X",
                            command=self.editor.cut_selected),
            _ContextMenuItem(icon="\U0001f4cb", label="Copy",
                            shortcut="Ctrl+C",
                            command=self.editor.copy_selected),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Lock Position",
                            command=lambda: self._toggle_locked(elem_idx)),
            _ContextMenuItem(label="Bring to Front",
                            command=lambda: self._bring_to_front(elem_idx)),
            _ContextMenuItem(label="Send to Back",
                            command=lambda: self._send_to_back(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\U0001f5d1", label="Delete",
                            shortcut="Delete",
                            command=self.editor.delete_selected_element),
        ]

    def _get_generic_element_menu(self, elem_idx):
        elem = self.editor.elements[elem_idx]
        etype = getattr(elem, "type_name", type(elem).__name__)
        icon = _TYPE_ICONS.get(etype, "\u2753")

        return [
            _ContextMenuItem(icon=icon, label=f"Edit {etype.title()}",
                            command=lambda: self._edit_element(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\u2702", label="Cut",
                            shortcut="Ctrl+X",
                            command=self.editor.cut_selected),
            _ContextMenuItem(icon="\U0001f4cb", label="Copy",
                            shortcut="Ctrl+C",
                            command=self.editor.copy_selected),
            _ContextMenuItem(icon="\U0001f4ea", label="Paste",
                            shortcut="Ctrl+V",
                            command=self.editor.paste_clipboard),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Lock Position",
                            command=lambda: self._toggle_locked(elem_idx)),
            _ContextMenuItem(label="Bring to Front",
                            command=lambda: self._bring_to_front(elem_idx)),
            _ContextMenuItem(label="Send to Back",
                            command=lambda: self._send_to_back(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\U0001f5d1", label="Delete",
                            shortcut="Delete",
                            command=self.editor.delete_selected_element),
        ]

    def _get_page_panel_menu(self, page_index):
        has_doc = self.editor.current_pdf is not None
        return [
            _ContextMenuItem(label="Go to Page",
                            command=lambda: self.editor.goto_page(page_index),
                            enabled=has_doc),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Insert Page Before",
                            command=lambda: self.editor.page_service.add_page(page_index),
                            enabled=has_doc),
            _ContextMenuItem(label="Insert Page After",
                            command=lambda: self.editor.page_service.add_page(page_index + 1),
                            enabled=has_doc),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Duplicate Page",
                            command=lambda: self.editor.page_service.duplicate_page(page_index),
                            enabled=has_doc),
            _ContextMenuItem(label="Delete Page",
                            command=lambda: self.editor.page_service.delete_page(page_index),
                            enabled=has_doc and self.editor.total_pages > 1),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Rotate Clockwise",
                            command=lambda: self.editor.page_service.rotate_page(page_index, 90),
                            enabled=has_doc),
            _ContextMenuItem(label="Rotate Counter-CW",
                            command=lambda: self.editor.page_service.rotate_page(page_index, -90),
                            enabled=has_doc),
        ]

    def _get_layer_panel_menu(self, elem_idx):
        return [
            _ContextMenuItem(label="Edit",
                            command=lambda: self._edit_element(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Move Up",
                            command=lambda: self._move_element(elem_idx, -1)),
            _ContextMenuItem(label="Move Down",
                            command=lambda: self._move_element(elem_idx, 1)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Bring to Front",
                            command=lambda: self._bring_to_front(elem_idx)),
            _ContextMenuItem(label="Send to Back",
                            command=lambda: self._send_to_back(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(label="Lock",
                            command=lambda: self._toggle_locked(elem_idx)),
            _ContextMenuItem(label="Toggle Visibility",
                            command=lambda: self._toggle_visibility(elem_idx)),
            _ContextMenuItem(separator=True),
            _ContextMenuItem(icon="\U0001f5d1", label="Delete",
                            shortcut="Delete",
                            command=self.editor.delete_selected_element),
        ]

    def _show_menu(self, x, y, items):
        self._dismiss_menu()
        theme = self.theme

        self._menu = tk.Toplevel(self.editor.root)
        self._menu.overrideredirect(True)
        self._menu.attributes("-topmost", True)
        self._menu.configure(bg=theme.get_color("menu_bg", ""),
                             highlightthickness=1,
                             highlightbackground=theme.get_color("surface", "border"))

        self._menu.geometry(f"+{x}+{y}")
        self._keyboard_index = 0

        for item in items:
            self._add_menu_item(item)

        self._menu.bind("<Escape>", lambda e: self._dismiss_menu())
        self._menu.bind("<FocusOut>", lambda e: self._dismiss_menu())

        self._menu.after(10, lambda: self._menu.focus_set())
        self._menu.bind("<Key>", self._on_key_nav)

        update_id = self._menu.after(50, self._update_menu_position)
        self._menu._update_id = update_id

    def _update_menu_position(self):
        if not self._menu or not self._menu.winfo_exists():
            return
        try:
            x = self._menu.winfo_x()
            y = self._menu.winfo_y()
            w = self._menu.winfo_width()
            h = self._menu.winfo_height()
            sw = self._menu.winfo_screenwidth()
            sh = self._menu.winfo_screenheight()

            if x + w > sw:
                x = sw - w - 4
            if y + h > sh:
                y = sh - h - 4

            self._menu.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _add_menu_item(self, item):
        theme = self.theme

        if item.separator:
            sep = tk.Frame(self._menu, bg=theme.get_color("separator", ""),
                           height=1)
            sep.pack(fill=tk.X, padx=8, pady=3)
            sep._is_separator = True
            return

        row = tk.Frame(self._menu, bg=theme.get_color("menu_bg", ""),
                       height=26, cursor="hand2" if item.enabled else "arrow")
        row.pack(fill=tk.X, padx=2, pady=1)
        row.pack_propagate(False)
        row._is_item = True
        row._item = item
        row._enabled = item.enabled

        bg = theme.get_color("menu_bg", "")
        fg = theme.get_color("text", "primary") if item.enabled else theme.get_color("text", "secondary")

        if item.icon:
            icon_label = tk.Label(row, text=item.icon,
                                  bg=bg, fg=fg,
                                  font=("Segoe UI", 10),
                                  width=3, anchor="center")
            icon_label.pack(side=tk.LEFT, padx=(4, 0))
        else:
            spacer = tk.Frame(row, bg=bg, width=20)
            spacer.pack(side=tk.LEFT)

        label = tk.Label(row, text=item.label,
                         bg=bg, fg=fg,
                         font=("Segoe UI", 9),
                         anchor="w")
        label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        if item.shortcut:
            sc_label = tk.Label(row, text=item.shortcut,
                                bg=bg,
                                fg=theme.get_color("text", "secondary"),
                                font=("Segoe UI", 8),
                                anchor="e")
            sc_label.pack(side=tk.RIGHT, padx=(0, 8))

        if item.submenu:
            arrow = tk.Label(row, text="\u25b6",
                             bg=bg, fg=fg,
                             font=("Segoe UI", 7),
                             padx=4)
            arrow.pack(side=tk.RIGHT)

        if item.enabled and item.command:
            for widget in [row, icon_label if item.icon else None, label,
                           row]:
                if widget:
                    widget.bind("<Button-1>",
                                lambda e, c=item.command: self._on_item_click(c))
                    widget.bind("<Enter>",
                                lambda e, r=row: r.configure(
                                    bg=theme.get_color("hover_bg", "")))
                    widget.bind("<Leave>",
                                lambda e, r=row, b=bg: r.configure(bg=b))

                    for child_label in [icon_label if item.icon else None, label,
                                        sc_label if item.shortcut else None,
                                        arrow if item.submenu else None]:
                        if child_label:
                            child_label.bind("<Button-1>",
                                             lambda e, c=item.command: self._on_item_click(c))
                            child_label.bind("<Enter>",
                                             lambda e, r=row: r.configure(
                                                 bg=theme.get_color("hover_bg", "")))
                            child_label.bind("<Leave>",
                                             lambda e, r=row, b=bg: r.configure(bg=b))

        if item.submenu:
            for widget in [row, label]:
                widget.bind("<Enter>",
                            lambda e, r=row, s=item.submenu: self._show_submenu(r, s))
            row.bind("<Leave>",
                     lambda e: self._dismiss_submenu())

    def _show_submenu(self, parent_row, submenu_items):
        self._dismiss_submenu()
        theme = self.theme

        submenu = tk.Toplevel(self._menu)
        submenu.overrideredirect(True)
        submenu.attributes("-topmost", True)
        submenu.configure(bg=theme.get_color("menu_bg", ""),
                          highlightthickness=1,
                          highlightbackground=theme.get_color("surface", "border"))

        px = parent_row.winfo_rootx() + parent_row.winfo_width()
        py = parent_row.winfo_rooty()
        submenu.geometry(f"+{px}+{py}")

        for item in submenu_items:
            if item.separator:
                sep = tk.Frame(submenu, bg=theme.get_color("separator", ""),
                               height=1)
                sep.pack(fill=tk.X, padx=8, pady=3)
            else:
                row = tk.Frame(submenu, bg=theme.get_color("menu_bg", ""),
                               height=24, cursor="hand2")
                row.pack(fill=tk.X, padx=2, pady=1)
                row.pack_propagate(False)

                bg = theme.get_color("menu_bg", "")
                fg = theme.get_color("text", "primary")

                label = tk.Label(row, text=item.label,
                                 bg=bg, fg=fg,
                                 font=("Segoe UI", 9), anchor="w")
                label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

                if item.shortcut:
                    sc = tk.Label(row, text=item.shortcut,
                                  bg=bg,
                                  fg=theme.get_color("text", "secondary"),
                                  font=("Segoe UI", 8))
                    sc.pack(side=tk.RIGHT, padx=4)

                for w in [row, label]:
                    w.bind("<Button-1>",
                           lambda e, c=item.command: self._on_submenu_click(c))
                    w.bind("<Enter>",
                           lambda e, r=row: r.configure(
                               bg=theme.get_color("hover_bg", "")))
                    w.bind("<Leave>",
                           lambda e, r=row, b=bg: r.configure(bg=b))

        self._menu._submenu = submenu

    def _dismiss_submenu(self):
        if self._menu and hasattr(self._menu, '_submenu'):
            sub = self._menu._submenu
            if sub and sub.winfo_exists():
                sub.destroy()
            self._menu._submenu = None

    def _on_item_click(self, command):
        self._dismiss_menu()
        if command:
            command()

    def _on_submenu_click(self, command):
        self._dismiss_menu()
        if command:
            command()

    def _on_key_nav(self, event):
        children = [c for c in self._menu.winfo_children()
                    if hasattr(c, '_is_item') and c._is_item]
        if not children:
            return

        if event.keysym == "Down":
            self._keyboard_index = min(self._keyboard_index + 1,
                                       len(children) - 1)
        elif event.keysym == "Up":
            self._keyboard_index = max(self._keyboard_index - 1, 0)
        elif event.keysym == "Return":
            if 0 <= self._keyboard_index < len(children):
                item = children[self._keyboard_index]._item
                if item.enabled and item.command:
                    self._on_item_click(item.command)
            return
        elif event.keysym == "Escape":
            self._dismiss_menu()
            return
        else:
            return

        theme = self.theme
        bg_hover = theme.get_color("hover_bg", "")
        bg_normal = theme.get_color("menu_bg", "")

        for i, child in enumerate(children):
            if i == self._keyboard_index:
                child.configure(bg=bg_hover)
            else:
                child.configure(bg=bg_normal)

    def _dismiss_menu(self):
        if self._menu:
            if hasattr(self._menu, '_update_id') and self._menu._update_id:
                try:
                    self._menu.after_cancel(self._menu._update_id)
                except Exception:
                    pass
            self._dismiss_submenu()
            try:
                self._menu.destroy()
            except Exception:
                pass
            self._menu = None

    def _edit_element(self, elem_idx):
        self.editor.selected_element = elem_idx
        self.editor.edit_selected_element()

    def _set_font_size(self, size):
        self.editor.set_font_size(size)

    def _toggle_locked(self, elem_idx):
        if elem_idx < len(self.editor.elements):
            elem = self.editor.elements[elem_idx]
            elem.locked = not getattr(elem, "locked", False)
            self.editor.canvas_manager.update_preview()

    def _toggle_visibility(self, elem_idx):
        if elem_idx < len(self.editor.elements):
            elem = self.editor.elements[elem_idx]
            elem.visible = not getattr(elem, "visible", True)
            self.editor.canvas_manager.update_preview()

    def _bring_to_front(self, elem_idx):
        if elem_idx < len(self.editor.elements):
            self.editor.undo_manager.save_state(self.editor.elements)
            elem = self.editor.elements.pop(elem_idx)
            self.editor.elements.append(elem)
            self.editor.selected_element = len(self.editor.elements) - 1
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()

    def _send_to_back(self, elem_idx):
        if elem_idx > 0 and elem_idx < len(self.editor.elements):
            self.editor.undo_manager.save_state(self.editor.elements)
            elem = self.editor.elements.pop(elem_idx)
            self.editor.elements.insert(0, elem)
            self.editor.selected_element = 0
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()

    def _move_element(self, elem_idx, direction):
        new_idx = elem_idx + direction
        if 0 <= new_idx < len(self.editor.elements):
            self.editor.undo_manager.save_state(self.editor.elements)
            self.editor.elements[elem_idx], self.editor.elements[new_idx] = \
                self.editor.elements[new_idx], self.editor.elements[elem_idx]
            if self.editor.selected_element == elem_idx:
                self.editor.selected_element = new_idx
            elif self.editor.selected_element == new_idx:
                self.editor.selected_element = elem_idx
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
