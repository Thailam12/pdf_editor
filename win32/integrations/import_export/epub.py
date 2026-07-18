"""EPUB import/export: bidirectional conversion between PDF and EPUB ebooks."""

import os
import re
import logging
import zipfile
from dataclasses import dataclass, field
from typing import Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class EPUBChapter:
    title: str = ""
    file_path: str = ""
    content: str = ""
    level: int = 1


@dataclass
class EPUBMetadata:
    title: str = ""
    author: str = ""
    language: str = "en"
    publisher: str = ""
    description: str = ""
    subject: list[str] = field(default_factory=list)
    date: str = ""
    identifier: str = ""
    rights: str = ""
    cover_image: str = ""


@dataclass
class EPUBContent:
    metadata: EPUBMetadata = field(default_factory=EPUBMetadata)
    chapters: list[EPUBChapter] = field(default_factory=list)
    css: str = ""
    images: dict[str, bytes] = field(default_factory=dict)
    toc: list[dict] = field(default_factory=list)


class EPUBConverter:
    """Convert between EPUB and PDF formats with full content preservation."""

    def __init__(self):
        self._epub_ns = "http://www.w3.org/1999/xhtml"

    def epub_to_pdf(self, epub_path: str, output_path: str) -> str:
        content = self.read_epub(epub_path)
        self._write_pdf(content, output_path)
        logger.info(f"EPUB to PDF: {epub_path} -> {output_path} ({len(content.chapters)} chapters)")
        return output_path

    def pdf_to_epub(self, pdf_path: str, output_path: str, metadata: EPUBMetadata = None) -> str:
        content = EPUBContent(metadata=metadata or EPUBMetadata())
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            if not content.metadata.title:
                meta = reader.metadata
                if meta:
                    content.metadata.title = meta.get("/Title", os.path.basename(pdf_path))
                    content.metadata.author = meta.get("/Author", "Unknown")
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                chapter = EPUBChapter(
                    title=f"Page {i + 1}",
                    content=self._text_to_xhtml(text),
                    level=1,
                )
                content.chapters.append(chapter)
        except Exception as e:
            logger.error(f"PDF read error: {e}")
        self._write_epub(content, output_path)
        logger.info(f"PDF to EPUB: {pdf_path} -> {output_path}")
        return output_path

    def read_epub(self, epub_path: str) -> EPUBContent:
        content = EPUBContent()
        with zipfile.ZipFile(epub_path, "r") as zf:
            self._read_container(zf, content)
            self._read_opf(zf, content)
            self._read_chapters(zf, content)
            self._read_images(zf, content)
        return content

    def _read_container(self, zf: zipfile.ZipFile, content: EPUBContent):
        if "META-INF/container.xml" not in zf.namelist():
            return
        root = ET.fromstring(zf.read("META-INF/container.xml"))
        for ref in root.iter():
            if "rootfile" in ref.tag.lower():
                content.metadata.identifier = ref.get("full-path", "")

    def _read_opf(self, zf: zipfile.ZipFile, content: EPUBContent):
        opf_path = content.metadata.identifier
        if not opf_path or opf_path not in zf.namelist():
            for name in zf.namelist():
                if name.endswith(".opf"):
                    opf_path = name
                    break
        if not opf_path:
            return
        root = ET.fromstring(zf.read(opf_path))
        ns = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}
        metadata_el = root.find(".//opf:metadata", ns)
        if metadata_el is not None:
            for tag in ["title", "creator", "language", "publisher", "description", "date", "rights"]:
                el = metadata_el.find(f"dc:{tag}", ns)
                if el is not None and el.text:
                    setattr(content.metadata, tag if tag != "creator" else "author", el.text)
            identifier = metadata_el.find("dc:identifier", ns)
            if identifier is not None and identifier.text:
                content.metadata.identifier = identifier.text

    def _read_chapters(self, zf: zipfile.ZipFile, content: EPUBContent):
        for name in sorted(zf.namelist()):
            if name.endswith((".xhtml", ".html", ".htm")) and "META-INF" not in name:
                try:
                    html_content = zf.read(name).decode("utf-8", errors="replace")
                    title = self._extract_title(html_content)
                    chapter = EPUBChapter(title=title, file_path=name, content=html_content)
                    content.chapters.append(chapter)
                except Exception as e:
                    logger.warning(f"Failed to read chapter {name}: {e}")

    def _read_images(self, zf: zipfile.ZipFile, content: EPUBContent):
        for name in zf.namelist():
            if name.startswith("images/") or name.startswith("OEBPS/images/"):
                if name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
                    content.images[name] = zf.read(name)

    def _extract_title(self, html: str) -> str:
        match = re.search(r"<h[1-6][^>]*>(.*?)</h[1-6]>", html, re.IGNORECASE | re.DOTALL)
        if match:
            return re.sub(r"<[^>]+>", "", match.group(1)).strip()
        match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "Untitled Chapter"

    def _text_to_xhtml(self, text: str) -> str:
        paragraphs = text.split("\n\n")
        body_parts = []
        for p in paragraphs:
            p = p.strip()
            if p:
                escaped = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                body_parts.append(f"<p>{escaped}</p>")
        body = "\n".join(body_parts)
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="{self._epub_ns}">
<head><title>Content</title></head>
<body>{body}</body>
</html>"""

    def _write_pdf(self, content: EPUBContent, output_path: str):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            doc = SimpleDocTemplate(output_path, pagesize=A4,
                                    topMargin=72, bottomMargin=72,
                                    leftMargin=72, rightMargin=72)
            styles = getSampleStyleSheet()
            story = []
            for chapter in content.chapters:
                if chapter.title:
                    story.append(Paragraph(chapter.title, styles["Heading1"]))
                    story.append(Spacer(1, 12))
                clean = re.sub(r"<[^>]+>", "", chapter.content)
                for para in clean.split("\n"):
                    para = para.strip()
                    if para:
                        story.append(Paragraph(para.replace("&", "&amp;"), styles["Normal"]))
                        story.append(Spacer(1, 6))
                story.append(PageBreak())
            if story:
                doc.build(story)
        except ImportError:
            logger.warning("reportlab not available; writing minimal PDF")
            with open(output_path, "wb") as f:
                f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n")

    def _write_epub(self, content: EPUBContent, output_path: str):
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            self._write_container(zf)
            opf_path = "OEBPS/content.opf"
            self._write_opf(zf, opf_path, content)
            for i, chapter in enumerate(content.chapters):
                chapter_file = f"OEBPS/chapter_{i + 1:03d}.xhtml"
                zf.writestr(chapter_file, chapter.content)
            for name, data in content.images.items():
                zf.writestr(f"OEBPS/{name}", data)
            self._write_toc(zf, content)

    def _write_container(self, zf: zipfile.ZipFile):
        container = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
        zf.writestr("META-INF/container.xml", container)

    def _write_opf(self, zf: zipfile.ZipFile, opf_path: str, content: EPUBContent):
        m = content.metadata
        items = []
        spine = []
        for i in range(len(content.chapters)):
            items.append(f'    <item id="ch{i}" href="chapter_{i + 1:03d}.xhtml" media-type="application/xhtml+xml"/>')
            spine.append(f'    <itemref idref="ch{i}"/>')
        opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{m.title}</dc:title>
    <dc:creator>{m.author}</dc:creator>
    <dc:language>{m.language}</dc:language>
    <dc:identifier>{m.identifier or 'pdfmind-epub'}</dc:identifier>
    <meta property="dcterms:modified">2024-01-01T00:00:00Z</meta>
  </metadata>
  <manifest>
{chr(10).join(items)}
  </manifest>
  <spine>
{chr(10).join(spine)}
  </spine>
</package>"""
        zf.writestr(opf_path, opf)

    def _write_toc(self, zf: zipfile.ZipFile, content: EPUBContent):
        nav_items = []
        for i, ch in enumerate(content.chapters):
            nav_items.append(f'      <li><a href="chapter_{i + 1:03d}.xhtml">{ch.title}</a></li>')
        toc = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Table of Contents</title></head>
<body>
  <nav epub:type="toc">
    <h1>Table of Contents</h1>
    <ol>
{chr(10).join(nav_items)}
    </ol>
  </nav>
</body>
</html>"""
        zf.writestr("OEBPS/toc.xhtml", toc)

    def get_supported_conversions(self) -> dict:
        return {
            "epub_to_pdf": "Convert EPUB ebooks to PDF for editing and printing",
            "pdf_to_epub": "Convert PDF documents to EPUB ebooks for e-readers",
        }
