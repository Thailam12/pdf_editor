import tkinter as tk

HANDLE_SIZE = 8


def _get_elem_type(elem):
    if isinstance(elem, tuple):
        return elem[0] if len(elem) > 1 else ""
    return getattr(elem, "type_name", "")


def _get_elem_page(elem):
    if isinstance(elem, tuple):
        return (elem[1] or {}).get("page", 0)
    return getattr(elem, "page", 0)


def _elem_to_params(elem):
    if isinstance(elem, tuple):
        return dict(elem[1]) if len(elem) > 1 else {}
    if hasattr(elem, "to_tuple"):
        return dict(elem.to_tuple()[1])
    return {}


class InteractionManager:
    def __init__(self, editor):
        self.editor = editor
        self.dragging = False
        self.drag_offset = None
        self.drag_orig_params = None

        self.resizing = False
        self.resize_handle = None
        self.resize_start = None
        self.resize_orig_params = None

    def get_resize_handle_at(self, x, y):
        canvas = self.editor.canvas_preview
        items = canvas.find_overlapping(x - HANDLE_SIZE, y - HANDLE_SIZE,
                                        x + HANDLE_SIZE, y + HANDLE_SIZE)
        for item in items:
            for tag in canvas.gettags(item):
                if tag.startswith("handle_"):
                    return tag
        return None

    def _find_element_id_at(self, x, y):
        canvas = self.editor.canvas_preview
        scale = self.editor.zoom_level / 100

        def eid_from_tag(tag):
            try:
                parts = tag.split("_")
                if len(parts) >= 2:
                    return int(parts[1])
            except (ValueError, IndexError):
                pass
            return None

        items = canvas.find_overlapping(x - 5, y - 5, x + 5, y + 5)
        for item in reversed(items):
            for tag in canvas.gettags(item):
                for prefix in ["text_", "img_", "shape_", "line_"]:
                    if tag.startswith(prefix):
                        eid = eid_from_tag(tag)
                        if eid is not None:
                            return eid

        px, py = x / scale, y / scale
        for i, elem in reversed(list(enumerate(self.editor.elements))):
            if _get_elem_page(elem) != self.editor.current_page:
                continue
            if isinstance(elem, tuple):
                etype, params = elem
                if etype == "line":
                    xmin, xmax = min(params['x1'], params['x2']), max(params['x1'], params['x2'])
                    ymin, ymax = min(params['y1'], params['y2']), max(params['y1'], params['y2'])
                else:
                    xmin, ymin = params.get('x', 0), params.get('y', 0)
                    xmax, ymax = xmin + params.get('w', 50), ymin + params.get('h', 20)
                if xmin - 5 <= px <= xmax + 5 and ymin - 5 <= py <= ymax + 5:
                    return i
            elif hasattr(elem, "contains_point") and elem.contains_point(px, py):
                return i
        return None

    def on_canvas_click(self, event):
        self.dragging = False
        self.resizing = False
        editor = self.editor

        handle = self.get_resize_handle_at(event.x, event.y)
        if handle:
            editor.selected_element = int(handle.split("_", 2)[1])
            self.resizing = True
            self.resize_handle = handle
            self.resize_start = (event.x, event.y)
            elem = editor.elements[editor.selected_element]
            self.resize_orig_params = _elem_to_params(elem)
            editor.canvas_manager.update_preview()
            return

        eid = self._find_element_id_at(event.x, event.y)
        if eid is None:
            editor.selected_element = None
            editor.canvas_manager.update_preview()
            return

        editor.selected_element = eid
        elem = editor.elements[eid]
        self.dragging = True
        scale = editor.zoom_level / 100

        if _get_elem_type(elem) == "line":
            if isinstance(elem, tuple):
                self.drag_offset = (event.x / scale - elem[1]['x1'],
                                    event.y / scale - elem[1]['y1'])
            else:
                self.drag_offset = (event.x / scale - elem.x1,
                                    event.y / scale - elem.y1)
        else:
            if isinstance(elem, tuple):
                ex = elem[1].get('x', 0)
                ey = elem[1].get('y', 0)
            else:
                ex, ey = elem.x, elem.y if hasattr(elem, 'x') else (0, 0)
                if hasattr(elem, 'x') and hasattr(elem, 'y'):
                    ex, ey = elem.x, elem.y
                elif hasattr(elem, 'get_bounds'):
                    ex, ey, _, _ = elem.get_bounds()
            self.drag_offset = (event.x / scale - ex, event.y / scale - ey)

        self.drag_orig_params = _elem_to_params(elem)
        editor.canvas_manager.update_preview()

    def on_canvas_drag(self, event):
        if self.editor.selected_element is None:
            return
        elem = self.editor.elements[self.editor.selected_element]
        scale = self.editor.zoom_level / 100

        if isinstance(elem, tuple):
            self._do_drag_tuple(event, elem, scale)
        else:
            if self.resizing:
                self._do_resize(event, elem, scale)
            elif self.dragging:
                self._do_drag(event, elem, scale)

        self.editor.canvas_manager.update_preview()

    def _do_drag_tuple(self, event, elem, scale):
        editor = self.editor
        etype, params = elem
        if self.resizing:
            dx = (event.x - self.resize_start[0]) / scale
            dy = (event.y - self.resize_start[1]) / scale
            corner = self.resize_handle.rsplit("_", 1)[-1]
            if etype == "text":
                orig_size = self.resize_orig_params.get("size", 12)
                params['size'] = max(8, int(orig_size + (dx + dy) / 2 * 0.6))
            elif etype in ("image", "rect", "ellipse", "triangle"):
                ow = self.resize_orig_params.get("w", 50)
                oh = self.resize_orig_params.get("h", 50)
                ox = self.resize_orig_params.get("x", 0)
                oy = self.resize_orig_params.get("y", 0)
                if "e" in corner:
                    params['w'] = max(10, ow + dx)
                if "s" in corner:
                    params['h'] = max(10, oh + dy)
                if "w" in corner:
                    dw = ow - dx
                    if dw > 10:
                        params['x'] = ox + dx
                        params['w'] = dw
                if "n" in corner:
                    dh = oh - dy
                    if dh > 10:
                        params['y'] = oy + dy
                        params['h'] = dh
        elif self.dragging:
            nx = max(0, event.x / scale - self.drag_offset[0])
            ny = max(0, event.y / scale - self.drag_offset[1])
            if etype == "line":
                dx = nx - self.drag_orig_params.get('x1', params['x1'])
                dy = ny - self.drag_orig_params.get('y1', params['y1'])
                params['x1'] = self.drag_orig_params.get('x1', params['x1']) + dx
                params['y1'] = self.drag_orig_params.get('y1', params['y1']) + dy
                params['x2'] = self.drag_orig_params.get('x2', params['x2']) + dx
                params['y2'] = self.drag_orig_params.get('y2', params['y2']) + dy
            else:
                params['x'] = nx
                params['y'] = ny

    def _do_resize(self, event, elem, scale):
        dx = (event.x - self.resize_start[0]) / scale
        dy = (event.y - self.resize_start[1]) / scale
        corner = self.resize_handle.rsplit("_", 1)[-1]

        etype = _get_elem_type(elem)
        if etype == "text":
            orig_size = self.resize_orig_params.get("size", 12)
            elem.size = max(8, int(orig_size + (dx + dy) / 2 * 0.6))
        elif etype in ("image", "shape"):
            ow = self.resize_orig_params.get("w", 50)
            oh = self.resize_orig_params.get("h", 50)
            ox = self.resize_orig_params.get("x", 0)
            oy = self.resize_orig_params.get("y", 0)
            if "e" in corner:
                elem.w = max(10, ow + dx)
            if "s" in corner:
                elem.h = max(10, oh + dy)
            if "w" in corner:
                dw = ow - dx
                if dw > 10:
                    elem.x = ox + dx
                    elem.w = dw
            if "n" in corner:
                dh = oh - dy
                if dh > 10:
                    elem.y = oy + dy
                    elem.h = dh

    def _do_drag(self, event, elem, scale):
        nx = max(0, event.x / scale - self.drag_offset[0])
        ny = max(0, event.y / scale - self.drag_offset[1])
        etype = _get_elem_type(elem)

        if etype == "text":
            elem.x, elem.y = nx, ny
        elif etype == "image":
            elem.x, elem.y = nx, ny
        elif etype == "shape":
            elem.x, elem.y = nx, ny
        elif etype == "line":
            orig = self.drag_orig_params
            dx = nx - (orig.get("x1", elem.x1) if orig else elem.x1)
            dy = ny - (orig.get("y1", elem.y1) if orig else elem.y1)
            if orig:
                elem.x1 = orig.get("x1", elem.x1)
                elem.y1 = orig.get("y1", elem.y1)
                elem.x2 = orig.get("x2", elem.x2)
                elem.y2 = orig.get("y2", elem.y2)
            elem.x1 += dx
            elem.y1 += dy
            elem.x2 += dx
            elem.y2 += dy

    def on_canvas_release(self, event):
        if self.dragging or self.resizing:
            self.editor.undo_manager.save_state(self.editor.elements)
            self.dragging = False
            self.resizing = False

    def on_canvas_motion(self, event):
        canvas = self.editor.canvas_preview
        if self.get_resize_handle_at(event.x, event.y):
            canvas.configure(cursor="arrow")
        elif self._find_element_id_at(event.x, event.y) is not None:
            canvas.configure(cursor="hand2")
        else:
            canvas.configure(cursor="cross")

    def show_context_menu(self, event):
        editor = self.editor
        eid = self._find_element_id_at(event.x, event.y)
        if eid is not None:
            editor.selected_element = eid
            editor.canvas_manager.update_preview()

        menu = tk.Menu(editor.root, tearoff=0)
        if editor.selected_element is not None:
            menu.add_command(label="Sửa", command=editor.edit_selected_element)
            menu.add_command(label="Xóa", command=editor.delete_selected_element)
            menu.add_separator()
        menu.add_command(label="Hủy", command=lambda: None)
        menu.tk_popup(event.x_root, event.y_root)
