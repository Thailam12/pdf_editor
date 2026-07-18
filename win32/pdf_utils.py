# -*- coding: utf-8 -*-
# pdf_utils.py
import os
import tempfile
import pymupdf
from PIL import Image, ImageTk
import mimetypes

class PDFUtils:
    def __init__(self):
        self.doc = None
        self.preview_photo = None

    def load_pdf(self, path):
        self.doc = pymupdf.open(path)

    def get_preview_image(self, scale=1.0, page_number=0):
        if not self.doc or page_number < 0 or page_number >= len(self.doc):
            return None
        page = self.doc[page_number]
        matrix = pymupdf.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.preview_photo = ImageTk.PhotoImage(img)
        return self.preview_photo

    @staticmethod
    def _normalize_color(color):
        if isinstance(color, str) and color.startswith("#") and len(color) == 7:
            r = int(color[1:3], 16) / 255.0
            g = int(color[3:5], 16) / 255.0
            b = int(color[5:7], 16) / 255.0
            return (r, g, b)
        return color

    @staticmethod
    def _normalize_rect(x, y, w, h):
        x2 = x + w
        y2 = y + h
        if x2 < x:
            x, x2 = x2, x
        if y2 < y:
            y, y2 = y2, y
        return pymupdf.Rect(x, y, x2, y2)

    @staticmethod
    def _map_font_name(font_name):
        font_map = {
            "Arial": "helv",
            "Times New Roman": "times",
            "Courier": "courier",
            "Calibri": "helv",
        }
        return font_map.get(font_name, font_name)

    @staticmethod
    def _alignment_value(alignment):
        return {
            "left": 0,
            "center": 1,
            "right": 2,
            "justify": 3,
        }.get(alignment, 0)

    def _normalize_element(self, elem):
        if isinstance(elem, (tuple, list)):
            return elem[0], elem[1]
        if hasattr(elem, 'to_tuple'):
            return elem.to_tuple()
        return "", {}

    def save_edited_pdf(self, input_path, output_path, elements):
        doc = pymupdf.open(input_path)
        try:
            for elem in elements:
                etype, params = self._normalize_element(elem)
                page_number = params.get("page", 0)
                if page_number < 0 or page_number >= len(doc):
                    continue
                page = doc[page_number]
                if etype == "text":
                    color = self._normalize_color(params.get("color", "#000000"))
                    font_name = self._map_font_name(params.get('font_name', "helv"))
                    font_size = params.get('size', 12)
                    align = self._alignment_value(params.get('alignment', 'left'))
                    text_len = len(params.get('text', ''))
                    text_width = max(100, text_len * (font_size * 0.6))
                    rect = self._normalize_rect(params['x'], params['y'], text_width, font_size * 2)
                    try:
                        page.insert_textbox(rect,
                                             params['text'],
                                             fontsize=font_size,
                                             fontname=font_name,
                                             color=color,
                                             align=align)
                    except Exception:
                        page.insert_text((params['x'], params['y']),
                                         params['text'],
                                         fontsize=font_size,
                                         fontname=font_name,
                                         color=color)
                    if params.get('underline'):
                        underline_y = params['y'] + font_size + 4
                        underline = self._normalize_rect(params['x'], underline_y, len(params['text']) * (font_size / 2), 1)
                        page.draw_rect(underline, color=color, fill=color)
                elif etype == "image":
                    image_path = params.get('path', '')
                    if os.path.exists(image_path):
                        rect = self._normalize_rect(params['x'], params['y'], params['w'], params['h'])
                        with open(image_path, 'rb') as img_stream:
                            page.insert_image(rect, stream=img_stream.read())
                elif etype == "line":
                    color = self._normalize_color(params.get('color', "#ff0000"))
                    page.draw_line((params['x1'], params['y1']), (params['x2'], params['y2']), color=color, width=params.get('width', 2))
                elif etype == "rect":
                    stroke = self._normalize_color(params.get('color', "#ff0000"))
                    rect = self._normalize_rect(params['x'], params['y'], params['w'], params['h'])
                    filled = bool(params.get('filled', False))
                    fill_color = self._normalize_color(params.get('fill_color', params.get('color', "#ff0000")))
                    page.draw_rect(rect, color=stroke, fill=(fill_color if filled else None), width=2)
                elif etype == "ellipse":
                    stroke = self._normalize_color(params.get('color', "#ff0000"))
                    rect = self._normalize_rect(params['x'], params['y'], params['w'], params['h'])
                    filled = bool(params.get('filled', False))
                    fill_color = self._normalize_color(params.get('fill_color', params.get('color', "#ff0000")))
                    page.draw_oval(rect, color=stroke, fill=(fill_color if filled else None), width=2)
                elif etype == "triangle":
                    stroke = self._normalize_color(params.get('color', "#ff0000"))
                    x = params['x']
                    y = params['y']
                    w = params['w']
                    h = params['h']
                    points = [x + w / 2, y, x, y + h, x + w, y + h]
                    filled = bool(params.get('filled', False))
                    fill_color = self._normalize_color(params.get('fill_color', params.get('color', "#ff0000")))
                    page.draw_polyline(points, color=stroke, fill=(fill_color if filled else None), width=2, closePath=True)

            if os.path.abspath(input_path) == os.path.abspath(output_path):
                directory, filename = os.path.split(output_path)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', dir=directory) as tmp_file:
                    temp_path = tmp_file.name
                doc.save(temp_path)
                doc.close()
                doc = None
                os.replace(temp_path, output_path)
                return True

            doc.save(output_path)
        finally:
            if doc is not None:
                doc.close()
        return True
