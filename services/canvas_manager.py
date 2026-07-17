import tkinter as tk
import math
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
