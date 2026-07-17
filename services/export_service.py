import os
import pymupdf
from tkinter import messagebox


class ExportService:
    def __init__(self, editor):
        self.editor = editor

    def export_to_images(self, output_dir, fmt="png", dpi=200):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            zoom = dpi / 72
            matrix = pymupdf.Matrix(zoom, zoom)
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                ext = "png" if fmt == "png" else "jpg"
                out_path = os.path.join(output_dir, f"page_{page_num + 1:04d}.{ext}")
                pix.save(out_path)
            self.editor.status.configure(
                text=f"Đã xuất {len(doc)} trang ra {fmt.upper()} tại {output_dir}"
            )
            messagebox.showinfo("Thành công", f"Đã xuất {len(doc)} trang thành công")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất ảnh: {str(e)}")

    def export_to_docx(self, output_path):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            try:
                from docx import Document
                from docx.shared import Pt
                has_docx = True
            except ImportError:
                has_docx = False

            if has_docx:
                word_doc = Document()
                for page_num in range(len(doc)):
                    if page_num > 0:
                        word_doc.add_page_break()
                    text = doc[page_num].get_text("text").strip()
                    if text:
                        word_doc.add_paragraph(text)
                word_doc.save(output_path)
            else:
                with open(output_path, "w", encoding="utf-8") as f:
                    for page_num in range(len(doc)):
                        text = doc[page_num].get_text("text").strip()
                        if text:
                            f.write(text + "\n\n")
            self.editor.status.configure(text=f"Đã xuất sang {os.path.basename(output_path)}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất DOCX: {str(e)}")

    def export_to_html(self, output_path):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None:
                return
            html_parts = [
                "<!DOCTYPE html>",
                "<html><head><meta charset='utf-8'><title>PDF Export</title>",
                "<style>body{font-family:Arial,sans-serif;margin:40px;}",
                ".page{margin-bottom:40px;padding:20px;border:1px solid #ccc;",
                "page-break-after:always;}</style></head><body>"
            ]
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").strip()
                html_parts.append(f"<div class='page'>")
                html_parts.append(f"<h2>Trang {page_num + 1}</h2>")
                if text:
                    lines = text.split("\n")
                    for line in lines:
                        if line.strip():
                            html_parts.append(f"<p>{self._escape_html(line)}</p>")
                html_parts.append("</div>")
            html_parts.append("</body></html>")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(html_parts))
            self.editor.status.configure(text=f"Đã xuất HTML sang {os.path.basename(output_path)}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất HTML: {str(e)}")

    def _escape_html(self, text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def export_page_as_image(self, page_num, output_path, dpi=200):
        try:
            doc = self.editor.pdf_utils.doc
            if doc is None or page_num < 0 or page_num >= len(doc):
                return
            page = doc[page_num]
            zoom = dpi / 72
            matrix = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            pix.save(output_path)
            self.editor.status.configure(text=f"Đã xuất trang {page_num + 1} thành ảnh")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất trang thành ảnh: {str(e)}")
