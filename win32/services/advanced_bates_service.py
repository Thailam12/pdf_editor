import os
import math
from datetime import datetime

import pymupdf


class AdvancedBatesService:
    def __init__(self, editor):
        self.editor = editor
        self._bates_log = []
        self._counter = 0

    def add_bates_number(self, page_num, prefix="", suffix="", start_num=1, num_format="{num:06d}",
                         position="bottom-right", font_size=10, font_name="Courier",
                         font_color="#000000", x_offset=0, y_offset=0):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return {"success": False, "error": "Invalid page number"}
            page = doc[page_num]
            bates_text = f"{prefix}{num_format.format(num=start_num)}{suffix}"
            rect = page.rect
            x, y = self._calculate_position(rect, position, font_size, x_offset, y_offset)
            writer = pymupdf.TextWriter(rect)
            font = pymupdf.Font(font_name)
            text_point = pymupdf.Point(x, y)
            writer.append(text_point, bates_text, font=font, fontsize=font_size)
            color = self._parse_color(font_color)
            writer.write_text(page, color=color)

            entry = {
                "page": page_num, "text": bates_text, "position": position,
                "font_size": font_size, "font_name": font_name,
            }
            self._bates_log.append(entry)
            self._counter = start_num + 1
            return {"success": True, "text": bates_text, "page": page_num}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_bates_all_pages(self, prefix="", suffix="", start_num=1, num_format="{num:06d}",
                            position="bottom-right", font_size=10, font_name="Courier",
                            font_color="#000000", page_range=None, x_offset=0, y_offset=0):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {"success": False, "error": "No document loaded"}
            total = len(doc)
            if page_range:
                start_page = max(0, page_range[0])
                end_page = min(total, page_range[1])
            else:
                start_page = 0
                end_page = total

            results = []
            num = start_num
            for pg in range(start_page, end_page):
                result = self.add_bates_number(
                    pg, prefix=prefix, suffix=suffix, start_num=num,
                    num_format=num_format, position=position,
                    font_size=font_size, font_name=font_name,
                    font_color=font_color, x_offset=x_offset, y_offset=y_offset,
                )
                results.append(result)
                num += 1
            success_count = len([r for r in results if r.get("success")])
            return {"success": True, "pages_processed": success_count, "total_pages": end_page - start_page}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_header_footer(self, page_num, header_text="", footer_text="", font_size=8,
                          font_name="Helvetica", font_color="#000000", position_header="top-center",
                          position_footer="bottom-center"):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {"success": False, "error": "No document loaded"}
            page = doc[page_num]
            rect = page.rect
            writer = pymupdf.TextWriter(rect)
            font = pymupdf.Font(font_name)
            color = self._parse_color(font_color)
            results = []
            if header_text:
                hx, hy = self._calculate_position(rect, position_header, font_size)
                writer.append(pymupdf.Point(hx, hy), header_text, font=font, fontsize=font_size)
                results.append("header")
            if footer_text:
                fx, fy = self._calculate_position(rect, position_footer, font_size)
                writer.append(pymupdf.Point(fx, fy), footer_text, font=font, fontsize=font_size)
                results.append("footer")
            writer.write_text(page, color=color)
            return {"success": True, "elements_added": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_date_stamp(self, page_num, date_format="%Y-%m-%d %H:%M", position="bottom-left",
                       font_size=8, font_name="Helvetica", font_color="#000000", custom_date=None):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {"success": False, "error": "No document loaded"}
            page = doc[page_num]
            rect = page.rect
            date_text = (custom_date or datetime.now()).strftime(date_format)
            writer = pymupdf.TextWriter(rect)
            font = pymupdf.Font(font_name)
            x, y = self._calculate_position(rect, position, font_size)
            writer.append(pymupdf.Point(x, y), date_text, font=font, fontsize=font_size)
            color = self._parse_color(font_color)
            writer.write_text(page, color=color)
            return {"success": True, "text": date_text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def add_exhibit_label(self, page_num, exhibit_label, position="top-center",
                          font_size=12, font_name="Helvetica-Bold", font_color="#000000"):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return {"success": False, "error": "No document loaded"}
            page = doc[page_num]
            rect = page.rect
            label_text = f"EXHIBIT {exhibit_label}"
            writer = pymupdf.TextWriter(rect)
            font = pymupdf.Font(font_name)
            x, y = self._calculate_position(rect, position, font_size)
            writer.append(pymupdf.Point(x, y), label_text, font=font, fontsize=font_size)
            color = self._parse_color(font_color)
            writer.write_text(page, color=color)
            return {"success": True, "text": label_text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_process_documents(self, file_paths, prefix="", start_num=1, num_format="{num:06d}",
                                position="bottom-right", font_size=10, font_name="Courier",
                                font_color="#000000", output_dir=None):
        if not output_dir:
            output_dir = os.path.dirname(file_paths[0]) if file_paths else "."
        os.makedirs(output_dir, exist_ok=True)
        results = []
        current_num = start_num
        for fpath in file_paths:
            try:
                doc = pymupdf.open(fpath)
                page_count = len(doc)
                for pg in range(page_count):
                    page = doc[pg]
                    bates_text = f"{prefix}{num_format.format(num=current_num)}"
                    rect = page.rect
                    writer = pymupdf.TextWriter(rect)
                    font = pymupdf.Font(font_name)
                    x, y = self._calculate_position(rect, position, font_size)
                    writer.append(pymupdf.Point(x, y), bates_text, font=font, fontsize=font_size)
                    color = self._parse_color(font_color)
                    writer.write_text(page, color=color)
                    current_num += 1
                base_name = os.path.splitext(os.path.basename(fpath))[0]
                out_path = os.path.join(output_dir, f"{base_name}_bates.pdf")
                doc.save(out_path, garbage=4, deflate=True)
                doc.close()
                results.append({"input": fpath, "output": out_path, "pages": page_count, "success": True})
            except Exception as e:
                results.append({"input": fpath, "error": str(e), "success": False})

        return {"success": True, "documents_processed": len(results), "results": results, "next_number": current_num}

    def _calculate_position(self, rect, position, font_size, x_offset=0, y_offset=0):
        margin = 20
        positions = {
            "top-left": (margin + x_offset, margin + font_size + y_offset),
            "top-center": (rect.width / 2 + x_offset, margin + font_size + y_offset),
            "top-right": (rect.width - margin + x_offset, margin + font_size + y_offset),
            "bottom-left": (margin + x_offset, rect.height - margin + y_offset),
            "bottom-center": (rect.width / 2 + x_offset, rect.height - margin + y_offset),
            "bottom-right": (rect.width - margin + x_offset, rect.height - margin + y_offset),
            "center": (rect.width / 2 + x_offset, rect.height / 2 + y_offset),
        }
        return positions.get(position, positions["bottom-right"])

    def _parse_color(self, color_str):
        if isinstance(color_str, (list, tuple)) and len(color_str) >= 3:
            return tuple(c / 255.0 if c > 1 else c for c in color_str[:3])
        if isinstance(color_str, str) and color_str.startswith("#") and len(color_str) == 7:
            r = int(color_str[1:3], 16) / 255.0
            g = int(color_str[3:5], 16) / 255.0
            b = int(color_str[5:7], 16) / 255.0
            return (r, g, b)
        return (0, 0, 0)

    def get_bates_log(self):
        return list(self._bates_log)

    def clear_bates_log(self):
        self._bates_log.clear()
        self._counter = 0

    def get_court_compliant_format(self, case_number, court_name, doc_title):
        return {
            "bates_header": f"Case: {case_number} | {court_name}",
            "bates_footer": f"{doc_title} | Confidential",
            "exhibit_format": "EXHIBIT {letter}",
            "number_format": "{prefix}{num:06d}{suffix}",
        }
