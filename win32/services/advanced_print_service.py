import os
import math
from datetime import datetime

import pymupdf


PAPER_SIZES = {
    "A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420),
    "A4": (210, 297), "A5": (148, 210), "A6": (105, 148), "A7": (74, 105),
    "A8": (52, 74), "A9": (37, 52), "A10": (26, 37),
    "Letter": (216, 279), "Legal": (216, 356), "Tabloid": (279, 432),
    "Executive": (184, 267), "Statement": (140, 216), "Folio": (216, 330),
    "Quarto": (215, 275), "10x14": (254, 356),
}

NUP_LAYOUTS = {
    1: {"cols": 1, "rows": 1},
    2: {"cols": 2, "rows": 1},
    4: {"cols": 2, "rows": 2},
    6: {"cols": 3, "rows": 2},
    8: {"cols": 4, "rows": 2},
    9: {"cols": 3, "rows": 3},
    16: {"cols": 4, "rows": 4},
}


class AdvancedPrintService:
    def __init__(self, editor):
        self.editor = editor
        self._paper_size = "A4"
        self._orientation = "portrait"
        self._margins = {"top": 20, "bottom": 20, "left": 20, "right": 20}
        self._color_mode = "color"
        self._duplex = False

    def set_paper_size(self, size):
        if size in PAPER_SIZES:
            self._paper_size = size
            return True
        return False

    def set_orientation(self, orientation):
        if orientation in ("portrait", "landscape"):
            self._orientation = orientation
            return True
        return False

    def set_margins(self, top=20, bottom=20, left=20, right=20):
        self._margins = {"top": top, "bottom": bottom, "left": left, "right": right}

    def set_color_mode(self, mode):
        if mode in ("color", "grayscale", "bw"):
            self._color_mode = mode
            return True
        return False

    def set_duplex(self, duplex=True):
        self._duplex = duplex

    def generate_print_preview(self, page_range=None):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {"success": False, "error": "No document loaded"}
            paper = PAPER_SIZES.get(self._paper_size, PAPER_SIZES["A4"])
            pw, ph = paper
            if self._orientation == "landscape":
                pw, ph = ph, pw
            pages = []
            if page_range:
                start = max(0, page_range[0])
                end = min(len(doc), page_range[1])
            else:
                start = 0
                end = len(doc)
            for pg in range(start, end):
                page_rect = doc[pg].rect
                scale_x = (pw - self._margins["left"] - self._margins["right"]) / page_rect.width
                scale_y = (ph - self._margins["top"] - self._margins["bottom"]) / page_rect.height
                scale = min(scale_x, scale_y)
                pages.append({
                    "page": pg + 1,
                    "scale": round(scale, 3),
                    "offset_x": self._margins["left"],
                    "offset_y": self._margins["top"],
                    "fits": True,
                })
            return {
                "success": True,
                "paper_size": self._paper_size,
                "paper_dimensions_mm": paper,
                "orientation": self._orientation,
                "margins": self._margins,
                "color_mode": self._color_mode,
                "duplex": self._duplex,
                "pages": pages,
                "total_pages": len(pages),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def print_nup(self, output_path, n=4, page_range=None, paper_size=None):
        paper = PAPER_SIZES.get(paper_size or self._paper_size, PAPER_SIZES["A4"])
        pw, ph = paper[0] * 72 / 25.4, paper[1] * 72 / 25.4
        if self._orientation == "landscape":
            pw, ph = ph, pw

        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {"success": False, "error": "No document loaded"}
            layout = NUP_LAYOUTS.get(n, NUP_LAYOUTS.get(4))
            cols, rows = layout["cols"], layout["rows"]
            cell_w = pw / cols
            cell_h = ph / rows

            if page_range:
                start = max(0, page_range[0])
                end = min(len(doc), page_range[1])
            else:
                start = 0
                end = len(doc)

            pages_per_sheet = cols * rows
            total_sheets = math.ceil((end - start) / pages_per_sheet)

            output = pymupdf.open()
            for sheet in range(total_sheets):
                out_page = output.new_page(width=pw, height=ph)
                for idx in range(pages_per_sheet):
                    src_idx = start + sheet * pages_per_sheet + idx
                    if src_idx >= end:
                        break
                    col = idx % cols
                    row = idx // cols
                    src_rect = doc[src_idx].rect
                    dest_x = col * cell_w + self._margins["left"] * 0.5
                    dest_y = row * cell_h + self._margins["top"] * 0.5
                    dest_w = cell_w - self._margins["left"] * 0.5
                    dest_h = cell_h - self._margins["top"] * 0.5
                    scale_x = dest_w / src_rect.width
                    scale_y = dest_h / src_rect.height
                    scale = min(scale_x, scale_y)
                    clip = src_rect
                    out_page.show_pdf_page(
                        pymupdf.Rect(dest_x, dest_y, dest_x + dest_w, dest_y + dest_h),
                        doc, src_idx, clip=clip, keep_proportion=True,
                    )

            output.save(output_path, garbage=4, deflate=True)
            output.close()
            return {"success": True, "output_path": output_path, "sheets": total_sheets, "nup": n}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def print_booklet(self, output_path, paper_size=None):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {"success": False, "error": "No document loaded"}
            paper = PAPER_SIZES.get(paper_size or self._paper_size, PAPER_SIZES["A4"])
            pw, ph = paper[0] * 72 / 25.4, paper[1] * 72 / 25.4
            half_pw = pw / 2

            total = len(doc)
            output = pymupdf.open()
            order = self._booklet_order(total)

            for i in range(0, len(order), 2):
                left_idx = order[i] if i < len(order) else -1
                right_idx = order[i + 1] if i + 1 < len(order) else -1
                out_page = output.new_page(width=pw, height=ph)

                if left_idx >= 0 and left_idx < total:
                    src_rect = doc[left_idx].rect
                    dest_rect = pymupdf.Rect(0, 0, half_pw, ph)
                    scale_x = dest_rect.width / src_rect.width
                    scale_y = dest_rect.height / src_rect.height
                    scale = min(scale_x, scale_y)
                    show_rect = pymupdf.Rect(
                        (ph - src_rect.height * scale) / 2 if scale > 1 else 0,
                        0,
                        src_rect.width * scale,
                        src_rect.height * scale,
                    )
                    out_page.show_pdf_page(dest_rect, doc, left_idx, clip=src_rect, keep_proportion=True)

                if right_idx >= 0 and right_idx < total:
                    src_rect = doc[right_idx].rect
                    dest_rect = pymupdf.Rect(half_pw, 0, pw, ph)
                    out_page.show_pdf_page(dest_rect, doc, right_idx, clip=src_rect, keep_proportion=True)

            output.save(output_path, garbage=4, deflate=True)
            output.close()
            return {"success": True, "output_path": output_path, "sheets": len(order) // 2}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _booklet_order(self, total):
        order = []
        pages = list(range(total))
        while pages:
            if len(pages) >= 2:
                order.append(pages.pop(0))
                order.append(pages.pop(-1))
            elif len(pages) == 1:
                order.append(pages.pop(0))
        return order

    def print_poster(self, output_path, across=2, down=2, page_num=0, paper_size=None):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {"success": False, "error": "No document loaded"}
            paper = PAPER_SIZES.get(paper_size or self._paper_size, PAPER_SIZES["A4"])
            pw, ph = paper[0] * 72 / 25.4, paper[1] * 72 / 25.4
            if self._orientation == "landscape":
                pw, ph = ph, pw

            output = pymupdf.open()
            total_w = pw * across
            total_h = ph * down

            for row in range(down):
                for col in range(across):
                    out_page = output.new_page(width=pw, height=ph)
                    src_rect = doc[page_num].rect
                    clip_x = col * src_rect.width / across
                    clip_y = row * src_rect.height / down
                    clip_w = src_rect.width / across
                    clip_h = src_rect.height / down
                    clip = pymupdf.Rect(clip_x, clip_y, clip_x + clip_w, clip_y + clip_h)
                    out_page.show_pdf_page(pymupdf.Rect(0, 0, pw, ph), doc, page_num, clip=clip, keep_proportion=False)

            output.save(output_path, garbage=4, deflate=True)
            output.close()
            return {"success": True, "output_path": output_path, "tiles": across * down}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_crop_marks(self, output_path, mark_length=10, offset=5):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {"success": False, "error": "No document loaded"}
            output = pymupdf.open()
            for pg in range(len(doc)):
                page = doc[pg]
                new_page = output.new_page(width=page.rect.width, height=page.rect.height)
                new_page.show_pdf_page(new_page.rect, doc, pg)
                rect = page.rect
                corners = [
                    (rect.x0, rect.y0, 1, 1),
                    (rect.x1, rect.y0, -1, 1),
                    (rect.x0, rect.y1, 1, -1),
                    (rect.x1, rect.y1, -1, -1),
                ]
                for cx, cy, dx, dy in corners:
                    shape = new_page.new_shape()
                    shape.draw_line(pymupdf.Point(cx + dx * offset, cy), pymupdf.Point(cx + dx * (offset + mark_length), cy))
                    shape.draw_line(pymupdf.Point(cx, cy + dy * offset), pymupdf.Point(cx, cy + dy * (offset + mark_length)))
                    shape.finish(width=0.5, color=(0, 0, 0))
                    shape.commit()

            output.save(output_path, garbage=4, deflate=True)
            output.close()
            return {"success": True, "output_path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_paper_sizes(self):
        return {name: {"width_mm": dims[0], "height_mm": dims[1]} for name, dims in PAPER_SIZES.items()}
