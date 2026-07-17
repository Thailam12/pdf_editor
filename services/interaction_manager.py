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


def _has_xy(elem):
    return hasattr(elem, "x") and hasattr(elem, "y")


def _get_xy(elem):
    if isinstance(elem, tuple):
        p = elem[1]
        return p.get("x", 0), p.get("y", 0)
    if _has_xy(elem):
        return elem.x, elem.y
    if hasattr(elem, "get_bounds"):
        bx, by, _, _ = elem.get_bounds()
        return bx, by
    return 0, 0


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
        self._freehand_drawing = False
        self._freehand_points = []

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
        all_prefixes = [
            "text_", "img_", "shape_", "line_", "hl_", "ann_", "note_",
            "stamp_", "sig_", "fh_", "link_", "redact_", "wm_", "ff_", "hf_",
        ]
        for item in reversed(items):
            for tag in canvas.gettags(item):
                for prefix in all_prefixes:
                    if tag.startswith(prefix):
                        eid = eid_from_tag(tag)
                        if eid is not None:
                            return eid

        px, py = x / scale, y / scale
        for i, elem in reversed(list(enumerate(self.editor.elements))):
            if _get_elem_page(elem) != self.editor.current_page:
                continue
            if getattr(elem, "locked", False):
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
        tool = getattr(editor, "active_tool", "select")

        if tool == "freehand":
            scale = editor.zoom_level / 100
            px, py = event.x / scale, event.y / scale
            if not self._freehand_drawing:
                self._freehand_drawing = True
                self._freehand_points = [(px, py)]
            else:
                self._freehand_points.append((px, py))
            return

        if tool == "eraser":
            eid = self._find_element_id_at(event.x, event.y)
            if eid is not None:
                editor.undo_manager.save_state(editor.elements)
                editor.elements.pop(eid)
                editor.selected_element = None
                editor.canvas_manager.update_preview()
                editor.status.configure(text="Element deleted")
            return

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
            ex, ey = _get_xy(elem)
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

    def on_canvas_release(self, event):
        if self._freehand_drawing and self._freehand_points:
            if len(self._freehand_points) >= 2:
                self.editor.undo_manager.save_state(self.editor.elements)
                from models.elements import FreehandElement
                color = getattr(self.editor, "stroke_color", "#FF0000")
                width = getattr(self.editor, "stroke_width", 2)
                elem = FreehandElement(
                    points=list(self._freehand_points),
                    color=color, width=width,
                    page=self.editor.current_page,
                )
                self.editor.elements.append(elem)
                self.editor.canvas_manager.update_preview()
                self.editor.status.configure(text="Freehand drawing added")
            self._freehand_drawing = False
            self._freehand_points = []
            return

        if self.dragging or self.resizing:
            self.editor.undo_manager.save_state(self.editor.elements)
            self.dragging = False
            self.resizing = False

    def on_canvas_motion(self, event):
        if self._freehand_drawing:
            return
        canvas = self.editor.canvas_preview
        if self.get_resize_handle_at(event.x, event.y):
            canvas.configure(cursor="arrow")
        elif self._find_element_id_at(event.x, event.y) is not None:
            canvas.configure(cursor="hand2")
        else:
            canvas.configure(cursor="cross")

    def _do_drag_tuple(self, event, elem, scale):
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
        elif etype in ("image", "shape", "highlight", "annotation",
                       "stamp", "signature", "link", "redact", "formfield"):
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

        if etype == "line":
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
        elif etype == "freehand":
            orig_pts = self.drag_orig_params.get("points", [])
            if orig_pts and hasattr(elem, "points"):
                ox_min = min(p[0] for p in orig_pts) if orig_pts else 0
                oy_min = min(p[1] for p in orig_pts) if orig_pts else 0
                new_x, new_y = nx, ny
                if self.drag_offset:
                    new_x = event.x / scale - self.drag_offset[0]
                    new_y = event.y / scale - self.drag_offset[1]
                dx = new_x - ox_min
                dy = new_y - oy_min
                elem.points = [(p[0] + dx, p[1] + dy) for p in orig_pts]
        elif etype == "note":
            elem.x = nx
            elem.y = ny
        elif etype == "watermark":
            elem.x = nx
            elem.y = ny
        elif _has_xy(elem):
            elem.x = nx
            elem.y = ny

    def show_context_menu(self, event):
        editor = self.editor
        eid = self._find_element_id_at(event.x, event.y)
        if eid is not None:
            editor.selected_element = eid
            editor.canvas_manager.update_preview()

        menu = tk.Menu(editor.root, tearoff=0)
        if editor.selected_element is not None:
            elem = editor.elements[editor.selected_element]
            etype = _get_elem_type(elem)
            menu.add_command(label="Edit", command=editor.edit_selected_element)
            menu.add_command(label="Delete", command=editor.delete_selected_element)
            menu.add_separator()
            menu.add_command(label="Bring to Front", command=lambda: self._reorder("front"))
            menu.add_command(label="Send to Back", command=lambda: self._reorder("back"))
            menu.add_command(label="Bring Forward", command=lambda: self._reorder("forward"))
            menu.add_command(label="Send Backward", command=lambda: self._reorder("backward"))
            menu.add_separator()
            if etype == "link" and hasattr(elem, "url"):
                menu.add_command(label="Open Link", command=lambda: editor.root.clipboard_clear() or editor.root.clipboard_append(elem.url))
        menu.add_command(label="Cancel", command=lambda: None)
        menu.tk_popup(event.x_root, event.y_root)

    def _reorder(self, direction):
        editor = self.editor
        idx = editor.selected_element
        if idx is None:
            return
        elems = editor.elements
        editor.undo_manager.save_state(elems)
        if direction == "front":
            elem = elems.pop(idx)
            elems.append(elem)
            editor.selected_element = len(elems) - 1
        elif direction == "back":
            elem = elems.pop(idx)
            elems.insert(0, elem)
            editor.selected_element = 0
        elif direction == "forward" and idx < len(elems) - 1:
            elems[idx], elems[idx + 1] = elems[idx + 1], elems[idx]
            editor.selected_element = idx + 1
        elif direction == "backward" and idx > 0:
            elems[idx], elems[idx - 1] = elems[idx - 1], elems[idx]
            editor.selected_element = idx - 1
        editor.canvas_manager.update_preview()
