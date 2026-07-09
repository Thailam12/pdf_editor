import tkinter as tk
from PIL import Image, ImageTk

HANDLE_SIZE = 8
HANDLE_COLOR = "#0078d7"
SELECTION_COLOR = "#0078d7"
TAG_PREFIXES = {"text": "text_", "image": "img_", "shape": "shape_", "line": "line_"}


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
            is_selected = i == self.editor.selected_element
            self._render_elem(canvas, elem, scale, is_selected, i)

    def _render_elem(self, canvas, elem, scale, selected, index):
        if isinstance(elem, tuple):
            self._render_tuple(canvas, elem, scale, selected, index)
            return
        etype = _elem_type(elem)
        if etype == "text":
            self._render_text(canvas, elem, scale, selected, index)
        elif etype == "image":
            self._render_image(canvas, elem, scale, selected, index)
        elif etype == "line":
            self._render_line(canvas, elem, scale, selected, index)
        elif etype == "shape":
            self._render_shape(canvas, elem, scale, selected, index)

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
            canvas.create_text(x + w / 2, y + h / 2, text="[Image Error]", anchor=tk.CENTER)
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

        tag = f"{TAG_PREFIXES['shape']}{index}"
        if elem.shape_type == "rect":
            canvas.create_rectangle(x, y, x + w, y + h, outline=stroke, fill=fill, width=2, tags=[tag])
        elif elem.shape_type == "ellipse":
            canvas.create_oval(x, y, x + w, y + h, outline=stroke, fill=fill, width=2, tags=[tag])
        elif elem.shape_type == "triangle":
            pts = [x + w / 2, y, x, y + h, x + w, y + h]
            canvas.create_polygon(pts, outline=stroke, fill=fill, width=2, tags=[tag])
        else:
            canvas.create_rectangle(x, y, x + w, y + h, outline=stroke, fill=fill, width=2, tags=[tag])
        if selected:
            self._draw_handles(canvas, x, y, w, h, index)

    def _draw_handles(self, canvas, x, y, w, h, index):
        half = HANDLE_SIZE // 2
        positions = [
            ("nw", x, y),
            ("n", x + w / 2, y),
            ("ne", x + w, y),
            ("w", x, y + h / 2),
            ("e", x + w, y + h / 2),
            ("sw", x, y + h),
            ("s", x + w / 2, y + h),
            ("se", x + w, y + h),
        ]
        for corner, hx, hy in positions:
            canvas.create_rectangle(
                hx - half, hy - half, hx + half, hy + half,
                fill="white", outline=HANDLE_COLOR, width=1.5,
                tags=[f"handle_{index}_{corner}"],
            )
