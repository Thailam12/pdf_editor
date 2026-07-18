import tkinter as tk
import math

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
        self._tail_dragging = False

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
            "meas_", "co_", "tb_", "vid_", "aud_", "bc_",
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
        self._tail_dragging = False
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

        if tool == "measurement":
            scale = editor.zoom_level / 100
            px, py = event.x / scale, event.y / scale
            if not hasattr(editor, "_measurement_points"):
                editor._measurement_points = []
            editor._measurement_points.append((px, py))
            if len(editor._measurement_points) >= 2:
                from models.elements import MeasurementElement
                pts = editor._measurement_points
                editor.undo_manager.save_state(editor.elements)
                elem = MeasurementElement(
                    x1=pts[0][0], y1=pts[0][1],
                    x2=pts[-1][0], y2=pts[-1][1],
                    points_list=list(pts),
                    measurement_type="distance" if len(pts) == 2 else "perimeter",
                    unit=getattr(editor, "measurement_unit", "mm"),
                    scale=getattr(editor, "measurement_scale", 1.0),
                    color=getattr(editor, "stroke_color", "#FF0000"),
                    page=editor.current_page,
                )
                editor.elements.append(elem)
                editor._measurement_points = []
                editor.canvas_manager.update_preview()
                editor.status.configure(text="Measurement added")
            else:
                editor.status.configure(text=f"Point {len(editor._measurement_points)} set - click to add more, double-click to finish")
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
        scale = editor.zoom_level / 100

        # Check for callout tail drag
        if _get_elem_type(elem) == "callout" and hasattr(elem, "tail_x"):
            tx_s, ty_s = elem.tail_x * scale, elem.tail_y * scale
            if abs(event.x - tx_s) < 12 and abs(event.y - ty_s) < 12:
                self._tail_dragging = True
                self.drag_offset = (event.x / scale - elem.tail_x,
                                    event.y / scale - elem.tail_y)
                self.drag_orig_params = _elem_to_params(elem)
                editor.canvas_manager.update_preview()
                return

        self.dragging = True
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

        if self._tail_dragging and _get_elem_type(elem) == "callout":
            elem.tail_x = max(0, event.x / scale - self.drag_offset[0])
            elem.tail_y = max(0, event.y / scale - self.drag_offset[1])
        elif isinstance(elem, tuple):
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

        if self.dragging or self.resizing or self._tail_dragging:
            if self._tail_dragging:
                self.editor.undo_manager.save_state(self.editor.elements)
            self.dragging = False
            self.resizing = False
            self._tail_dragging = False

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

    def on_canvas_double_click(self, event):
        editor = self.editor
        eid = self._find_element_id_at(event.x, event.y)
        if eid is None:
            return
        editor.selected_element = eid
        elem = editor.elements[eid]
        etype = _get_elem_type(elem)

        if etype == "textbox":
            self._edit_textbox_text(elem)
        elif etype == "video":
            self._show_media_properties(elem, "Video")
        elif etype == "audio":
            self._show_media_properties(elem, "Audio")
        elif etype == "callout":
            self._edit_callout_text(elem)
        editor.canvas_manager.update_preview()

    def _edit_textbox_text(self, elem):
        editor = self.editor
        dialog = tk.Toplevel(editor.root)
        dialog.title("Edit Text Box")
        dialog.geometry("400x300")
        dialog.transient(editor.root)
        dialog.grab_set()

        tk.Label(dialog, text="Text:").pack(anchor="w", padx=10, pady=(10, 0))
        text_var = tk.StringVar(value=elem.text)
        text_widget = tk.Text(dialog, height=10, wrap="word")
        text_widget.pack(fill="both", expand=True, padx=10, pady=5)
        text_widget.insert("1.0", elem.text)
        text_widget.focus_set()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)

        def apply_text():
            editor.undo_manager.save_state(editor.elements)
            elem.text = text_widget.get("1.0", "end-1c")
            editor.canvas_manager.update_preview()
            dialog.destroy()

        tk.Button(btn_frame, text="OK", command=apply_text, width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10).pack(side="left", padx=5)

    def _edit_callout_text(self, elem):
        editor = self.editor
        dialog = tk.Toplevel(editor.root)
        dialog.title("Edit Callout Text")
        dialog.geometry("400x300")
        dialog.transient(editor.root)
        dialog.grab_set()

        tk.Label(dialog, text="Text:").pack(anchor="w", padx=10, pady=(10, 0))
        text_widget = tk.Text(dialog, height=10, wrap="word")
        text_widget.pack(fill="both", expand=True, padx=10, pady=5)
        text_widget.insert("1.0", elem.text)
        text_widget.focus_set()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)

        def apply_text():
            editor.undo_manager.save_state(editor.elements)
            elem.text = text_widget.get("1.0", "end-1c")
            editor.canvas_manager.update_preview()
            dialog.destroy()

        tk.Button(btn_frame, text="OK", command=apply_text, width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10).pack(side="left", padx=5)

    def _show_media_properties(self, elem, media_type):
        editor = self.editor
        dialog = tk.Toplevel(editor.root)
        dialog.title(f"{media_type} Properties")
        dialog.geometry("350x200")
        dialog.transient(editor.root)
        dialog.grab_set()

        info_frame = tk.Frame(dialog)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(info_frame, text=f"{media_type} Properties",
                 font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        tk.Label(info_frame, text=f"File: {elem.file_path or 'None'}",
                 anchor="w", wraplength=320).pack(anchor="w")
        if hasattr(elem, "duration"):
            tk.Label(info_frame, text=f"Duration: {elem.duration}s",
                     anchor="w").pack(anchor="w")
        if hasattr(elem, "w"):
            tk.Label(info_frame, text=f"Size: {int(elem.w)} x {int(elem.h)}",
                     anchor="w").pack(anchor="w")
        if hasattr(elem, "poster_image_path") and elem.poster_image_path:
            tk.Label(info_frame, text=f"Poster: {elem.poster_image_path}",
                     anchor="w", wraplength=320).pack(anchor="w")

        tk.Button(dialog, text="Close", command=dialog.destroy, width=10).pack(pady=10)

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
                       "stamp", "signature", "link", "redact", "formfield",
                       "textbox", "video", "barcode", "callout"):
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

        if etype in ("line", "measurement"):
            orig = self.drag_orig_params
            if orig:
                x1_key, y1_key = ("x1", "y1")
                dx = nx - (orig.get(x1_key, elem.x1))
                dy = ny - (orig.get(y1_key, elem.y1))
                elem.x1 = orig.get(x1_key, elem.x1)
                elem.y1 = orig.get(y1_key, elem.y1)
                elem.x2 = orig.get("x2", elem.x2)
                elem.y2 = orig.get("y2", elem.y2)
                elem.x1 += dx
                elem.y1 += dy
                elem.x2 += dx
                elem.y2 += dy
                if etype == "measurement" and hasattr(elem, "points_list") and elem.points_list:
                    elem.points_list = [(p[0] + dx, p[1] + dy) for p in orig.get("points_list", elem.points_list)]
        elif etype == "callout":
            elem.x = nx
            elem.y = ny
            if self.drag_orig_params:
                orig_tx = self.drag_orig_params.get("tail_x", elem.tail_x)
                orig_ty = self.drag_orig_params.get("tail_y", elem.tail_y)
                dx = nx - self.drag_orig_params.get("x", elem.x)
                dy = ny - self.drag_orig_params.get("y", elem.y)
                elem.tail_x = orig_tx + dx
                elem.tail_y = orig_ty + dy
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
