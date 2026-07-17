import tkinter as tk
import math
import os
from PIL import Image, ImageTk

HANDLE_SIZE = 8
HANDLE_COLOR = "#0078d7"
SELECTION_COLOR = "#0078d7"
TAG_PREFIXES = {
    "text": "text_", "image": "img_", "shape": "shape_", "line": "line_",
    "highlight": "hl_", "annotation": "ann_", "note": "note_",
    "stamp": "stamp_", "signature": "sig_", "freehand": "fh_",
    "link": "link_", "redact": "redact_", "watermark": "wm_",
    "formfield": "ff_", "headerfooter": "hf_",
    "measurement": "meas_", "callout": "co_", "textbox": "tb_",
    "video": "vid_", "audio": "aud_", "barcode": "bc_",
}


def _elem_type(elem):
    if isinstance(elem, tuple):
        return elem[0]
    return getattr(elem, "type_name", "")


def _elem_page(elem):
    if isinstance(elem, tuple):
        return (elem[1] or {}).get("page", 0)
    return getattr(elem, "page", 0)


class CanvasManager:
    def __init__(self, editor):
        self.editor = editor

    def update_preview(self):
        canvas = self.editor.canvas_preview
        canvas.delete("all")
        scale = self.editor.zoom_level / 100

        img_tk = self.editor.pdf_utils.get_preview_image(scale, self.editor.current_page)
        if img_tk:
            canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.editor.pdf_utils.preview_photo = img_tk

        self.editor.element_images.clear()
        for i, elem in enumerate(self.editor.elements):
            if _elem_page(elem) != self.editor.current_page:
                continue
            if not getattr(elem, "visible", True):
                continue
            is_selected = i == self.editor.selected_element
            self._render_elem(canvas, elem, scale, is_selected, i)

    def _render_elem(self, canvas, elem, scale, selected, index):
        if isinstance(elem, tuple):
            self._render_tuple(canvas, elem, scale, selected, index)
            return
        etype = _elem_type(elem)
        renderers = {
            "text": self._render_text,
            "image": self._render_image,
            "line": self._render_line,
            "shape": self._render_shape,
            "highlight": self._render_highlight,
            "annotation": self._render_annotation,
            "note": self._render_note,
            "stamp": self._render_stamp,
            "signature": self._render_signature,
            "freehand": self._render_freehand,
            "link": self._render_link,
            "redact": self._render_redact,
            "watermark": self._render_watermark,
            "formfield": self._render_formfield,
            "headerfooter": self._render_headerfooter,
            "measurement": self._render_measurement,
            "callout": self._render_callout,
            "textbox": self._render_textbox,
            "video": self._render_video,
            "audio": self._render_audio,
            "barcode": self._render_barcode,
        }
        renderer = renderers.get(etype)
        if renderer:
            renderer(canvas, elem, scale, selected, index)

    def _render_tuple(self, canvas, elem, scale, selected, index):
        etype, params = elem
        x, y = params.get("x", 0) * scale, params.get("y", 0) * scale
        w, h = params.get("w", 50) * scale, params.get("h", 20) * scale
        tag_prefix = TAG_PREFIXES.get(etype, "elem_")
        tag = f"{tag_prefix}{index}"

        if etype == "text":
            fs = max(1, int(params.get("size", 12) * scale))
            canvas.create_text(x, y, text=params.get("text", ""),
                               font=(params.get("font_name", "Arial"), fs),
                               fill=params.get("color", "#000"), anchor="nw", tags=[tag])
        elif etype == "image":
            canvas.create_rectangle(x, y, x + w, y + h, fill="#ccc", outline="#999", tags=[tag])
        elif etype == "line":
            canvas.create_line(params["x1"] * scale, params["y1"] * scale,
                               params["x2"] * scale, params["y2"] * scale,
                               fill=params.get("color", "red"), width=params.get("width", 2), tags=[tag])
        elif etype in ("rect", "ellipse", "triangle"):
            stroke = SELECTION_COLOR if selected else params.get("color", "red")
            fill = params.get("fill_color", "") if params.get("filled") else ""
            if etype == "rect":
                canvas.create_rectangle(x, y, x + w, y + h, outline=stroke, fill=fill, width=2, tags=[tag])
            elif etype == "ellipse":
                canvas.create_oval(x, y, x + w, y + h, outline=stroke, fill=fill, width=2, tags=[tag])
            elif etype == "triangle":
                pts = [x + w / 2, y, x, y + h, x + w, y + h]
                canvas.create_polygon(pts, outline=stroke, fill=fill, width=2, tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_text(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        fs = max(1, int(elem.size * scale))
        style = ""
        if elem.bold:
            style += "bold "
        if elem.italic:
            style += "italic"
        font_spec = (elem.font_name, fs, style.strip()) if style else (elem.font_name, fs)
        color = elem.color if not selected else SELECTION_COLOR

        item = canvas.create_text(x, y, text=elem.text, font=font_spec,
                                  fill=color, anchor="nw",
                                  tags=[f"{TAG_PREFIXES['text']}{index}"])
        if selected:
            bx, by, bw, bh = canvas.bbox(item) if item else (x, y, x + 100, y + 20)
            if bx and by:
                pad = 4
                canvas.create_rectangle(bx - pad, by - pad, bw + pad, bh + pad,
                                        outline=SELECTION_COLOR, width=1, dash=(3, 2),
                                        tags=[f"sel_{index}"])
                bw = bw - bx
                bh = bh - by
                self._draw_handles(canvas, bx, by, bw, bh, index)

    def _render_image(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        photo = None
        try:
            img = Image.open(elem.path)
            img = img.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.editor.element_images.append(photo)
        except Exception:
            pass
        if photo:
            canvas.create_image(x, y, image=photo, anchor=tk.NW,
                                tags=[f"{TAG_PREFIXES['image']}{index}"])
        else:
            canvas.create_rectangle(x, y, x + w, y + h, fill="#ccc", outline="#999",
                                    tags=[f"{TAG_PREFIXES['image']}{index}"])
            canvas.create_text(x + w / 2, y + h / 2, text="[Image]", anchor=tk.CENTER)
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_line(self, canvas, elem, scale, selected, index):
        x1, y1 = elem.x1 * scale, elem.y1 * scale
        x2, y2 = elem.x2 * scale, elem.y2 * scale
        color = elem.color if not selected else SELECTION_COLOR
        canvas.create_line(x1, y1, x2, y2, fill=color, width=elem.width,
                           tags=[f"{TAG_PREFIXES['line']}{index}"])
        if selected:
            bx, by = min(x1, x2) - 10, min(y1, y2) - 10
            bw = abs(x2 - x1) + 20
            bh = abs(y2 - y1) + 20
            self._draw_handles(canvas, bx, by, bw, bh, index)

    def _render_shape(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        stroke = elem.color if not selected else SELECTION_COLOR
        fill = elem.fill_color if elem.filled else ""
        sw = getattr(elem, "stroke_width", 2)
        tag = f"{TAG_PREFIXES['shape']}{index}"
        if elem.shape_type == "rect":
            canvas.create_rectangle(x, y, x + w, y + h, outline=stroke, fill=fill, width=sw, tags=[tag])
        elif elem.shape_type == "ellipse":
            canvas.create_oval(x, y, x + w, y + h, outline=stroke, fill=fill, width=sw, tags=[tag])
        elif elem.shape_type == "triangle":
            pts = [x + w / 2, y, x, y + h, x + w, y + h]
            canvas.create_polygon(pts, outline=stroke, fill=fill, width=sw, tags=[tag])
        else:
            canvas.create_rectangle(x, y, x + w, y + h, outline=stroke, fill=fill, width=sw, tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_highlight(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tag = f"{TAG_PREFIXES['highlight']}{index}"
        canvas.create_rectangle(x, y, x + w, y + h, fill=elem.color,
                                outline="", stipple="gray50", tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_annotation(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tag = f"{TAG_PREFIXES['annotation']}{index}"
        sw = max(1, int(elem.stroke_width * scale))
        if elem.style == "underline":
            canvas.create_line(x, y + h, x + w, y + h, fill=elem.color,
                               width=sw, tags=[tag])
        elif elem.style == "strikethrough":
            canvas.create_line(x, y + h / 2, x + w, y + h / 2, fill=elem.color,
                               width=sw, tags=[tag])
        elif elem.style == "squiggly":
            pts = []
            for i in range(int(w / 6) + 1):
                px = x + i * 6
                py = y + h / 2 + (3 if i % 2 == 0 else -3)
                pts.extend([px, py])
            if len(pts) >= 4:
                canvas.create_line(pts, fill=elem.color, width=sw, smooth=True, tags=[tag])
        else:
            canvas.create_rectangle(x, y, x + w, y + h, fill=elem.color,
                                    outline="", tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_note(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        sz = elem.size * scale
        tag = f"{TAG_PREFIXES['note']}{index}"
        canvas.create_polygon(x, y, x + sz, y, x + sz, y + sz,
                              x + sz * 0.65, y + sz * 0.65, x, y + sz,
                              fill=elem.color, outline="", tags=[tag])
        canvas.create_text(x + sz * 0.5, y + sz * 0.35, text="!",
                           font=("Arial", int(9 * scale), "bold"),
                           fill="#000", anchor=tk.CENTER, tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, sz, sz, index)

    def _render_stamp(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tag = f"{TAG_PREFIXES['stamp']}{index}"
        color = elem.color
        sw = max(1, int(3 * scale))
        canvas.create_rectangle(x, y, x + w, y + h, outline=color, width=sw, tags=[tag])
        fs = max(1, int(elem.font_size * scale))
        style = "bold" if elem.bold else ""
        canvas.create_text(x + w / 2, y + h / 2, text=elem.text,
                           font=(elem.font_name, fs, style),
                           fill=color, anchor=tk.CENTER, tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_signature(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tag = f"{TAG_PREFIXES['signature']}{index}"
        if elem.image_data:
            try:
                import base64
                data = elem.image_data
                if "," in data:
                    data = data.split(",", 1)[1]
                img_bytes = base64.b64decode(data)
                from io import BytesIO
                img = Image.open(BytesIO(img_bytes))
                img = img.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.editor.element_images.append(photo)
                canvas.create_image(x, y, image=photo, anchor=tk.NW, tags=[tag])
                if selected:
                    self._draw_handles(canvas, x, y, w, h, index)
                return
            except Exception:
                pass
        fs = max(1, int(min(h * 0.6, 20 * scale)))
        canvas.create_text(x + w / 2, y + h / 2, text=elem.text or "Signature",
                           font=("Brush Script MT", fs, "italic"),
                           fill=elem.color, anchor=tk.CENTER, tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_freehand(self, canvas, elem, scale, selected, index):
        pts = elem.points
        if len(pts) < 2:
            return
        tag = f"{TAG_PREFIXES['freehand']}{index}"
        flat_pts = []
        for px, py in pts:
            flat_pts.extend([px * scale, py * scale])
        sw = max(1, int(elem.width * scale))
        canvas.create_line(flat_pts, fill=elem.color, width=sw,
                           smooth=True, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=[tag])
        if selected:
            bx, by, bw, bh = self._freehand_bounds(elem, scale)
            self._draw_handles(canvas, bx, by, bw, bh, index)

    def _render_link(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tag = f"{TAG_PREFIXES['link']}{index}"
        canvas.create_rectangle(x, y, x + w, y + h, fill="#E6F2FF",
                                outline=elem.color, width=1, dash=(4, 2), tags=[tag])
        fs = max(1, int(11 * scale))
        text = elem.text or elem.url or "[Link]"
        if len(text) > 30:
            text = text[:27] + "..."
        canvas.create_text(x + 4 * scale, y + h / 2, text=text,
                           font=("Arial", fs), fill=elem.color, anchor="w", tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_redact(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tag = f"{TAG_PREFIXES['redact']}{index}"
        canvas.create_rectangle(x, y, x + w, y + h, fill=elem.color,
                                outline="#FF0000", width=2, tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_watermark(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        fs = max(1, int(elem.size * scale))
        tag = f"{TAG_PREFIXES['watermark']}{index}"
        canvas.create_text(x, y, text=elem.text, font=(elem.font_name, fs),
                           fill=elem.color, anchor="nw", tags=[tag])
        if selected:
            bw = len(elem.text) * fs * 0.6
            bh = fs * 2
            self._draw_handles(canvas, x, y, bw, bh, index)

    def _render_formfield(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tag = f"{TAG_PREFIXES['formfield']}{index}"
        canvas.create_rectangle(x, y, x + w, y + h, fill="#FFFFFF",
                                outline="#999999", width=1, tags=[tag])
        fs = max(1, int(elem.font_size * scale))
        if elem.value:
            canvas.create_text(x + 4 * scale, y + h / 2, text=elem.value,
                               font=("Arial", fs), fill=elem.color, anchor="w", tags=[tag])
        if elem.field_name:
            canvas.create_text(x + w + 4 * scale, y + h / 2, text=f"[{elem.field_name}]",
                               font=("Arial", max(1, int(8 * scale))), fill="#999", anchor="w")
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_headerfooter(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        fs = max(1, int(elem.size * scale))
        tag = f"{TAG_PREFIXES['headerfooter']}{index}"
        total = self.editor.total_pages
        current = self.editor.current_page + 1
        text = elem.text.replace("{page}", str(current)).replace("{total}", str(total))
        text = text.replace("{date}", "")
        canvas.create_text(x, y, text=text, font=(elem.font_name, fs),
                           fill=elem.color, anchor="nw", tags=[tag])
        if selected:
            bw = len(text) * fs * 0.5
            self._draw_handles(canvas, x, y, bw, fs * 2, index)

    def _render_measurement(self, canvas, elem, scale, selected, index):
        tag = f"{TAG_PREFIXES['measurement']}{index}"
        color = elem.color if not selected else SELECTION_COLOR
        sw = max(1, int(elem.width * scale))
        fs = max(1, int(elem.font_size * scale))
        mt = elem.measurement_type

        if mt == "area" and elem.points_list and len(elem.points_list) >= 3:
            pts = []
            for px, py in elem.points_list:
                pts.extend([px * scale, py * scale])
            canvas.create_polygon(pts, fill="#FF000020", outline=color,
                                  width=sw, stipple="gray25", tags=[tag])
            if elem.show_label:
                label = f"{elem.get_area():.2f} {elem.unit}\u00B2"
                xs = [p[0] * scale for p in elem.points_list]
                ys = [p[1] * scale for p in elem.points_list]
                cx = sum(xs) / len(xs)
                cy = sum(ys) / len(ys)
                canvas.create_text(cx, cy, text=label, font=("Arial", fs),
                                   fill=color, anchor=tk.CENTER, tags=[tag])
        elif mt == "perimeter" and elem.points_list and len(elem.points_list) >= 2:
            flat_pts = []
            for px, py in elem.points_list:
                flat_pts.extend([px * scale, py * scale])
            if len(elem.points_list) > 2:
                flat_pts.extend([elem.points_list[0][0] * scale,
                                 elem.points_list[0][1] * scale])
            canvas.create_line(flat_pts, fill=color, width=sw, tags=[tag])
            if elem.show_label:
                total = 0
                for i in range(len(elem.points_list) - 1):
                    dx = (elem.points_list[i + 1][0] - elem.points_list[i][0]) * scale
                    dy = (elem.points_list[i + 1][1] - elem.points_list[i][1]) * scale
                    seg_len = math.sqrt(dx * dx + dy * dy)
                    mid_x = (elem.points_list[i][0] + elem.points_list[i + 1][0]) / 2 * scale
                    mid_y = (elem.points_list[i][1] + elem.points_list[i + 1][1]) / 2 * scale
                    seg_label = f"{seg_len / elem.scale:.1f}{elem.unit}" if elem.scale else f"{seg_len:.1f}{elem.unit}"
                    canvas.create_text(mid_x, mid_y - fs, text=seg_label,
                                       font=("Arial", fs), fill=color,
                                       anchor=tk.CENTER, tags=[tag])
                    total += seg_len
                label = f"P={total / elem.scale:.2f}{elem.unit}" if elem.scale else f"P={total:.2f}{elem.unit}"
                cx = sum(p[0] * scale for p in elem.points_list) / len(elem.points_list)
                cy = sum(p[1] * scale for p in elem.points_list) / len(elem.points_list)
                canvas.create_text(cx, cy + fs * 2, text=label,
                                   font=("Arial", fs, "bold"), fill=color,
                                   anchor=tk.CENTER, tags=[tag])
        else:
            x1, y1 = elem.x1 * scale, elem.y1 * scale
            x2, y2 = elem.x2 * scale, elem.y2 * scale
            canvas.create_line(x1, y1, x2, y2, fill=color, width=sw, tags=[tag])
            arrow_len = 10 * scale
            for (ax, ay, bx, by) in [(x1, y1, x2, y2), (x2, y2, x1, y1)]:
                angle = math.atan2(by - ay, bx - ax)
                left_angle = angle + math.radians(150)
                right_angle = angle - math.radians(150)
                canvas.create_line(ax, ay,
                                   ax + arrow_len * math.cos(left_angle),
                                   ay + arrow_len * math.sin(left_angle),
                                   fill=color, width=sw, tags=[tag])
                canvas.create_line(ax, ay,
                                   ax + arrow_len * math.cos(right_angle),
                                   ay + arrow_len * math.sin(right_angle),
                                   fill=color, width=sw, tags=[tag])
            if elem.show_label:
                length = elem.get_length()
                label = f"{length:.2f} {elem.unit}"
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                canvas.create_text(mx, my - fs * 1.2, text=label,
                                   font=("Arial", fs), fill=color,
                                   anchor=tk.CENTER, tags=[tag])

        bx, by, bw, bh = elem.get_bounds()
        if selected:
            self._draw_handles(canvas, bx * scale, by * scale,
                               bw * scale, bh * scale, index)

    def _render_callout(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tx, ty = elem.tail_x * scale, elem.tail_y * scale
        tag = f"{TAG_PREFIXES['callout']}{index}"
        sw = max(1, int(elem.border_width * scale))
        r = min(8 * scale, w / 4, h / 4)

        canvas.create_rectangle(x + r, y, x + w - r, y + h,
                                fill=elem.fill_color, outline="", tags=[tag])
        canvas.create_rectangle(x, y + r, x + w, y + h - r,
                                fill=elem.fill_color, outline="", tags=[tag])
        canvas.create_oval(x, y, x + 2 * r, y + 2 * r,
                           fill=elem.fill_color, outline="", tags=[tag])
        canvas.create_oval(x + w - 2 * r, y, x + w, y + 2 * r,
                           fill=elem.fill_color, outline="", tags=[tag])
        canvas.create_oval(x, y + h - 2 * r, x + 2 * r, y + h,
                           fill=elem.fill_color, outline="", tags=[tag])
        canvas.create_oval(x + w - 2 * r, y + h - 2 * r, x + w, y + h,
                           fill=elem.fill_color, outline="", tags=[tag])

        # border
        canvas.create_arc(x, y, x + 2 * r, y + 2 * r, start=90, extent=90,
                          outline=elem.border_color, width=sw, style=tk.ARC, tags=[tag])
        canvas.create_arc(x + w - 2 * r, y, x + w, y + 2 * r, start=0, extent=90,
                          outline=elem.border_color, width=sw, style=tk.ARC, tags=[tag])
        canvas.create_arc(x + w - 2 * r, y + h - 2 * r, x + w, y + h,
                          start=270, extent=90, outline=elem.border_color,
                          width=sw, style=tk.ARC, tags=[tag])
        canvas.create_arc(x, y + h - 2 * r, x + 2 * r, y + h,
                          start=180, extent=90, outline=elem.border_color,
                          width=sw, style=tk.ARC, tags=[tag])
        canvas.create_line(x + r, y, x + w - r, y, fill=elem.border_color,
                           width=sw, tags=[tag])
        canvas.create_line(x + r, y + h, x + w - r, y + h,
                           fill=elem.border_color, width=sw, tags=[tag])
        canvas.create_line(x, y + r, x, y + h - r, fill=elem.border_color,
                           width=sw, tags=[tag])
        canvas.create_line(x + w, y + r, x + w, y + h - r,
                           fill=elem.border_color, width=sw, tags=[tag])

        # tail triangle
        tail_base_w = min(20 * scale, w * 0.3)
        if tx < x:
            tbx = x
            tby = y + h / 2
        elif tx > x + w:
            tbx = x + w
            tby = y + h / 2
        elif ty < y:
            tbx = x + w / 2
            tby = y
        elif ty > y + h:
            tbx = x + w / 2
            tby = y + h
        else:
            tbx = x + w / 2
            tby = y + h
        canvas.create_polygon(tbx, tby, tx, ty,
                              tbx + tail_base_w * 0.3, tby + (10 * scale if ty < tby else -10 * scale),
                              fill=elem.fill_color, outline=elem.border_color,
                              width=sw, tags=[tag])

        # text with word wrap
        fs = max(1, int(elem.font_size * scale))
        pad = max(1, int(4 * scale))
        text_color = elem.text_color
        if elem.text:
            max_text_w = max(1, w - 2 * pad)
            words = elem.text.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                tw = canvas.create_text(0, 0, text=test_line,
                                        font=(elem.font_name, fs), anchor="nw")
                bbox = canvas.bbox(tw)
                canvas.delete(tw)
                if bbox and (bbox[2] - bbox[0]) > max_text_w and current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = test_line
            if current_line:
                lines.append(current_line)
            line_h = fs * 1.2
            total_h = line_h * len(lines)
            start_y = y + (h - total_h) / 2
            for i, line in enumerate(lines):
                canvas.create_text(x + pad, start_y + i * line_h, text=line,
                                   font=(elem.font_name, fs), fill=text_color,
                                   anchor="nw", tags=[tag])

        if selected:
            bx, by, bw, bh = elem.get_bounds()
            self._draw_handles(canvas, bx * scale, by * scale,
                               bw * scale, bh * scale, index)

    def _render_textbox(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tag = f"{TAG_PREFIXES['textbox']}{index}"
        sw = max(1, int(elem.border_width * scale))

        if elem.fill_color:
            canvas.create_rectangle(x, y, x + w, y + h, fill=elem.fill_color,
                                    outline=elem.border_color, width=sw, tags=[tag])
        else:
            canvas.create_rectangle(x, y, x + w, y + h, fill="",
                                    outline=elem.border_color, width=sw, tags=[tag])

        fs = max(1, int(elem.font_size * scale))
        pad = max(1, int(elem.padding * scale))
        if elem.text:
            max_text_w = max(1, w - 2 * pad)
            words = elem.text.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                tw = canvas.create_text(0, 0, text=test_line,
                                        font=(elem.font_name, fs), anchor="nw")
                bbox = canvas.bbox(tw)
                canvas.delete(tw)
                if bbox and (bbox[2] - bbox[0]) > max_text_w and current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    current_line = test_line
            if current_line:
                lines.append(current_line)
            line_h = fs * 1.2
            total_h = line_h * len(lines)
            start_y = y + (h - total_h) / 2
            for i, line_text in enumerate(lines):
                lw = len(line_text) * fs * 0.6
                if elem.alignment == "center":
                    lx = x + (w - lw) / 2
                    anchor = "n"
                elif elem.alignment == "right":
                    lx = x + w - pad
                    anchor = "ne"
                else:
                    lx = x + pad
                    anchor = "nw"
                canvas.create_text(lx, start_y + i * line_h, text=line_text,
                                   font=(elem.font_name, fs), fill=elem.color,
                                   anchor=anchor, tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_video(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tag = f"{TAG_PREFIXES['video']}{index}"

        photo = None
        if elem.poster_image_path:
            try:
                img = Image.open(elem.poster_image_path)
                img = img.resize((max(1, int(w)), max(1, int(h))), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.editor.element_images.append(photo)
            except Exception:
                pass

        if photo:
            canvas.create_image(x, y, image=photo, anchor=tk.NW, tags=[tag])
        canvas.create_rectangle(x, y, x + w, y + h, fill="#1a1a2e" if not photo else "",
                                outline="#444", width=1, tags=[tag])

        # dark overlay
        canvas.create_rectangle(x, y, x + w, y + h, fill="#000000",
                                outline="", stipple="gray50", tags=[tag])

        # play button
        play_r = min(w, h) * 0.2
        cx, cy = x + w / 2, y + h / 2
        canvas.create_oval(cx - play_r, cy - play_r, cx + play_r, cy + play_r,
                           fill="#FFFFFF80", outline="white", width=2, tags=[tag])
        tri_pts = [cx - play_r * 0.3, cy - play_r * 0.6,
                   cx - play_r * 0.3, cy + play_r * 0.6,
                   cx + play_r * 0.5, cy]
        canvas.create_polygon(tri_pts, fill="white", outline="", tags=[tag])

        # label
        fs = max(1, int(10 * scale))
        fname = os.path.basename(elem.file_path) if elem.file_path else "Video"
        if len(fname) > 25:
            fname = fname[:22] + "..."
        canvas.create_text(x + 4 * scale, y + h - fs * 1.5, text=fname,
                           font=("Arial", fs), fill="white", anchor="nw", tags=[tag])

        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_audio(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = 200 * scale, 40 * scale
        tag = f"{TAG_PREFIXES['audio']}{index}"

        canvas.create_rectangle(x, y, x + w, y + h, fill="#E8E8E8",
                                outline="#999", width=1, tags=[tag])

        # play button
        play_r = h * 0.25
        cx, cy = x + h / 2, y + h / 2
        canvas.create_oval(cx - play_r, cy - play_r, cx + play_r, cy + play_r,
                           fill="#0066CC", outline="", tags=[tag])
        tri_pts = [cx - play_r * 0.3, cy - play_r * 0.5,
                   cx - play_r * 0.3, cy + play_r * 0.5,
                   cx + play_r * 0.4, cy]
        canvas.create_polygon(tri_pts, fill="white", outline="", tags=[tag])

        # sound waves (decorative)
        for i in range(3):
            wave_x = cx + play_r + (i + 1) * 6 * scale
            wave_r = (i + 1) * 4 * scale
            canvas.create_arc(wave_x - wave_r, cy - wave_r, wave_x + wave_r, cy + wave_r,
                              start=300, extent=120, outline="#0066CC",
                              width=max(1, int(1.5 * scale)), style=tk.ARC, tags=[tag])

        # label
        fs = max(1, int(9 * scale))
        fname = os.path.basename(elem.file_path) if elem.file_path else "Audio"
        if len(fname) > 25:
            fname = fname[:22] + "..."
        canvas.create_text(x + h / 2 + play_r + 20 * scale, y + h / 2,
                           text=fname, font=("Arial", fs), fill="#333",
                           anchor="w", tags=[tag])

        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _render_barcode(self, canvas, elem, scale, selected, index):
        x, y = elem.x * scale, elem.y * scale
        w, h = elem.w * scale, elem.h * scale
        tag = f"{TAG_PREFIXES['barcode']}{index}"

        canvas.create_rectangle(x, y, x + w, y + h, fill=elem.background_color,
                                outline="#CCC", width=1, tags=[tag])

        if elem.barcode_type == "qr":
            grid_size = 21
            cell_w = w / grid_size
            cell_h = h / grid_size
            data_hash = hash(elem.data) if elem.data else 0
            rng = data_hash
            # finder patterns
            def draw_finder(fx, fy):
                for r in range(7):
                    for c in range(7):
                        is_edge = r == 0 or r == 6 or c == 0 or c == 6
                        is_inner = 2 <= r <= 4 and 2 <= c <= 4
                        if is_edge or is_inner:
                            canvas.create_rectangle(
                                fx + c * cell_w, fy + r * cell_h,
                                fx + (c + 1) * cell_w, fy + (r + 1) * cell_h,
                                fill=elem.color, outline="", tags=[tag])

            draw_finder(x, y)
            draw_finder(x + (grid_size - 7) * cell_w, y)
            draw_finder(x, y + (grid_size - 7) * cell_h)

            # data modules
            for r in range(grid_size):
                for c in range(grid_size):
                    if (r < 8 and c < 8) or (r < 8 and c >= grid_size - 8) or (r >= grid_size - 8 and c < 8):
                        continue
                    rng = ((rng * 1103515245 + 12345) & 0x7FFFFFFF)
                    if rng % 3 != 0:
                        canvas.create_rectangle(
                            x + c * cell_w, y + r * cell_h,
                            x + (c + 1) * cell_w, y + (r + 1) * cell_h,
                            fill=elem.color, outline="", tags=[tag])
        else:
            # 1D barcode
            data_bytes = (elem.data or "0").encode("utf-8")
            num_bars = min(40, max(10, len(data_bytes) * 3))
            bar_w = w / num_bars
            for i in range(num_bars):
                byte_val = data_bytes[i % len(data_bytes)] if data_bytes else i
                bar_width_ratio = ((byte_val >> (i % 4)) & 1) + 1
                bw = bar_w * bar_width_ratio
                if bw > bar_w:
                    bw = bar_w
                if i % 2 == 0 or byte_val & 1:
                    canvas.create_rectangle(
                        x + i * bar_w, y, x + i * bar_w + bw, y + h * 0.85,
                        fill=elem.color, outline="", tags=[tag])

        if elem.show_text:
            fs = max(1, int(elem.font_size * scale))
            display_text = elem.data if elem.data else ""
            if len(display_text) > 30:
                display_text = display_text[:27] + "..."
            canvas.create_text(x + w / 2, y + h - fs, text=display_text,
                               font=("Arial", fs), fill=elem.color,
                               anchor=tk.CENTER, tags=[tag])

        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _freehand_bounds(self, elem, scale):
        pts = elem.points
        if not pts:
            return (0, 0, 10, 10)
        xs = [p[0] * scale for p in pts]
        ys = [p[1] * scale for p in pts]
        return (min(xs), min(ys), max(xs) - min(xs) or 5, max(ys) - min(ys) or 5)

    def _draw_handles(self, canvas, x, y, w, h, index):
        half = HANDLE_SIZE // 2
        positions = [
            ("nw", x, y), ("n", x + w / 2, y), ("ne", x + w, y),
            ("w", x, y + h / 2), ("e", x + w, y + h / 2),
            ("sw", x, y + h), ("s", x + w / 2, y + h), ("se", x + w, y + h),
        ]
        for corner, hx, hy in positions:
            canvas.create_rectangle(
                hx - half, hy - half, hx + half, hy + half,
                fill="white", outline=HANDLE_COLOR, width=1.5,
                tags=[f"handle_{index}_{corner}"],
            )
