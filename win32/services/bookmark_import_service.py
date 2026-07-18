import os
import pymupdf


class BookmarkImportService:
    def __init__(self, editor):
        self.editor = editor

    def import_from_pdf(self, path):
        """Import bookmarks/outlines from a PDF file. Returns list of bookmark dicts."""
        try:
            doc = pymupdf.open(path)
            toc = doc.get_toc(simple=True)
            doc.close()
            bookmarks = []
            for i, entry in enumerate(toc):
                level = entry[0]
                title = entry[1]
                page = entry[2] if len(entry) > 2 else 0
                bookmarks.append({
                    "title": title,
                    "level": level,
                    "page": page,
                    "index": i
                })
            return bookmarks
        except Exception as e:
            raise RuntimeError(f"Cannot import bookmarks from PDF: {e}")

    def import_from_html(self, path):
        """Import bookmarks from an HTML file with anchor links."""
        try:
            bookmarks = []
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            heading_pattern = re.compile(
                r'<h(\d)[^>]*id=["\']?([^"\'>\s]*)["\']?[^>]*>(.*?)</h\1>',
                re.IGNORECASE | re.DOTALL
            )
            for match in heading_pattern.finditer(content):
                level = int(match.group(1))
                anchor_id = match.group(2)
                text = re.sub(r'<[^>]+>', '', match.group(3)).strip()
                bookmarks.append({
                    "title": text,
                    "level": level,
                    "page": 0,
                    "anchor": anchor_id,
                    "index": len(bookmarks)
                })
            return bookmarks
        except Exception as e:
            raise RuntimeError(f"Cannot import bookmarks from HTML: {e}")

    def import_from_outline_file(self, path):
        """Import bookmarks from a text outline file (indented text format)."""
        try:
            bookmarks = []
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                stripped = line.rstrip()
                if not stripped:
                    continue
                level = 1
                title = stripped.lstrip()
                indent = len(stripped) - len(title)
                if indent > 0:
                    level = max(1, indent // 2 + 1)
                bookmarks.append({
                    "title": title,
                    "level": level,
                    "page": 0,
                    "index": i
                })
            return bookmarks
        except Exception as e:
            raise RuntimeError(f"Cannot import bookmarks from outline file: {e}")

    def export_to_html(self, bookmarks, output_path):
        """Export bookmarks to an HTML file with nested list structure."""
        try:
            html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Bookmarks</title>
<style>
.bookmarks { font-family: Arial, sans-serif; }
.level-1 { font-size: 16px; font-weight: bold; margin-top: 10px; }
.level-2 { font-size: 14px; margin-left: 20px; }
.level-3 { font-size: 12px; margin-left: 40px; }
.level-4 { font-size: 12px; margin-left: 60px; }
a { text-decoration: none; color: #0066CC; }
a:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="bookmarks">
<h1>Document Bookmarks</h1>
<ul>
"""
            current_level = 0
            for bm in bookmarks:
                level = bm.get("level", 1)
                title = bm.get("title", "")
                page = bm.get("page", 0)
                while current_level < level:
                    html += "<ul>\n"
                    current_level += 1
                while current_level > level:
                    html += "</ul>\n"
                    current_level -= 1
                html += f'<li class="level-{level}">'
                html += f'<a href="#page-{page}">{title}</a>'
                html += "</li>\n"
            while current_level > 0:
                html += "</ul>\n"
                current_level -= 1
            html += """</ul>
</div>
</body>
</html>"""
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            return True
        except Exception as e:
            raise RuntimeError(f"Cannot export bookmarks to HTML: {e}")

    def export_to_txt(self, bookmarks, output_path):
        """Export bookmarks to a text file with indentation."""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for bm in bookmarks:
                    level = bm.get("level", 1)
                    title = bm.get("title", "")
                    page = bm.get("page", "")
                    indent = "  " * (level - 1)
                    f.write(f"{indent}{title}")
                    if page:
                        f.write(f" (p. {page})")
                    f.write("\n")
            return True
        except Exception as e:
            raise RuntimeError(f"Cannot export bookmarks to text: {e}")

    def sync_bookmarks_with_headings(self, path):
        """Synchronize PDF bookmarks with detected headings in the document."""
        try:
            doc = pymupdf.open(path)
            new_toc = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                blocks = page.get_text("dict").get("blocks", [])
                for block in blocks:
                    if block.get("type") == 0:
                        lines = block.get("lines", [])
                        for line in lines:
                            spans = line.get("spans", [])
                            for span in spans:
                                font_size = span.get("size", 12)
                                text = span.get("text", "").strip()
                                if font_size >= 18 and text:
                                    level = 1 if font_size >= 24 else 2
                                    new_toc.append([level, text, page_num + 1])
                                elif font_size >= 15 and text:
                                    new_toc.append([3, text, page_num + 1])
            if new_toc:
                doc.set_toc(new_toc)
            doc.save(path)
            doc.close()
            return [
                {"level": e[0], "title": e[1], "page": e[2]}
                for e in new_toc
            ]
        except Exception as e:
            raise RuntimeError(f"Cannot sync bookmarks: {e}")
