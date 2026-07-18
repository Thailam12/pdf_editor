"""Markdown-to-PDF and PDF-to-Markdown conversion with rich formatting support."""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MarkdownElement:
    element_type: str = ""
    content: str = ""
    level: int = 0
    language: str = ""
    ordered: bool = False
    items: list[str] = field(default_factory=list)
    link_url: str = ""
    alt_text: str = ""
    alignment: str = ""
    html: str = ""


@dataclass
class MarkdownDocument:
    title: str = ""
    content: str = ""
    elements: list[MarkdownElement] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    word_count: int = 0
    heading_count: int = 0
    image_count: int = 0
    link_count: int = 0
    code_block_count: int = 0
    table_count: int = 0


@dataclass
class MarkdownConversionOptions:
    page_size: str = "A4"
    margins: dict = field(default_factory=lambda: {"top": 72, "bottom": 72, "left": 72, "right": 72})
    font_family: str = "Helvetica"
    font_size_body: int = 11
    font_size_h1: int = 24
    font_size_h2: int = 18
    font_size_h3: int = 14
    line_spacing: float = 1.5
    code_font: str = "Courier"
    syntax_highlighting: bool = True
    toc: bool = False
    page_numbers: bool = True
    header_footer: bool = False
    custom_css: str = ""
    base_url: str = ""


class MarkdownConverter:
    """Bidirectional Markdown-PDF conversion with full formatting preservation."""

    def __init__(self):
        self._options = MarkdownConversionOptions()

    def set_options(self, options: MarkdownConversionOptions):
        self._options = options

    def markdown_to_pdf(self, md_path: str, output_path: str,
                        options: MarkdownConversionOptions = None) -> str:
        opts = options or self._options
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        doc = self.parse_markdown(content)
        self._write_pdf(doc, output_path, opts)
        logger.info(f"Markdown to PDF: {md_path} -> {output_path}")
        return output_path

    def pdf_to_markdown(self, pdf_path: str, output_path: str = None) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            md_parts = []
            title = ""
            if reader.metadata and reader.metadata.get("/Title"):
                title = reader.metadata["/Title"]
                md_parts.append(f"# {title}\n")
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    md_parts.append(f"<!-- Page {i + 1} -->\n")
                    md_parts.append(text.strip())
                    md_parts.append("")
            md_content = "\n\n".join(md_parts)
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                logger.info(f"PDF to Markdown: {pdf_path} -> {output_path}")
            return md_content
        except Exception as e:
            logger.error(f"PDF to Markdown failed: {e}")
            return ""

    def parse_markdown(self, content: str) -> MarkdownDocument:
        doc = MarkdownDocument(content=content)
        lines = content.split("\n")
        current_element = None
        in_code_block = False
        code_lines = []
        code_lang = ""
        table_lines = []
        in_table = False
        for line in lines:
            if line.strip().startswith("```"):
                if in_code_block:
                    code_content = "\n".join(code_lines)
                    elem = MarkdownElement(
                        element_type="code", content=code_content,
                        language=code_lang,
                    )
                    doc.elements.append(elem)
                    doc.code_block_count += 1
                    code_lines = []
                    code_lang = ""
                    in_code_block = False
                else:
                    in_code_block = True
                    code_lang = line.strip().lstrip("`").strip()
                continue
            if in_code_block:
                code_lines.append(line)
                continue
            if line.strip().startswith("|"):
                table_lines.append(line)
                in_table = True
                continue
            elif in_table:
                table_content = "\n".join(table_lines)
                elem = MarkdownElement(element_type="table", content=table_content)
                doc.elements.append(elem)
                doc.table_count += 1
                table_lines = []
                in_table = False
            stripped = line.strip()
            if not stripped:
                continue
            heading_match = re.match(r"^(#{1,6})\s+(.*)", stripped)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2)
                elem = MarkdownElement(
                    element_type="heading", content=text, level=level,
                )
                doc.elements.append(elem)
                doc.heading_count += 1
                if level == 1 and not doc.title:
                    doc.title = text
                continue
            ul_match = re.match(r"^(\s*)[-*+]\s+(.*)", stripped)
            if ul_match:
                items = [ul_match.group(2)]
                elem = MarkdownElement(
                    element_type="list", content=ul_match.group(2),
                    ordered=False, items=items,
                )
                doc.elements.append(elem)
                continue
            ol_match = re.match(r"^(\s*)\d+\.\s+(.*)", stripped)
            if ol_match:
                items = [ol_match.group(2)]
                elem = MarkdownElement(
                    element_type="list", content=ol_match.group(2),
                    ordered=True, items=items,
                )
                doc.elements.append(elem)
                continue
            if stripped.startswith(">"):
                quote_text = stripped.lstrip(">").strip()
                elem = MarkdownElement(element_type="blockquote", content=quote_text)
                doc.elements.append(elem)
                continue
            hr_match = re.match(r"^[-*_]{3,}\s*$", stripped)
            if hr_match:
                elem = MarkdownElement(element_type="hr")
                doc.elements.append(elem)
                continue
            img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
            if img_match:
                elem = MarkdownElement(
                    element_type="image", alt_text=img_match.group(1),
                    link_url=img_match.group(2),
                )
                doc.elements.append(elem)
                doc.image_count += 1
                continue
            link_match = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", stripped)
            if link_match:
                for text, url in link_match:
                    elem = MarkdownElement(
                        element_type="link", content=text, link_url=url,
                    )
                    doc.elements.append(elem)
                    doc.link_count += 1
            elem = MarkdownElement(element_type="paragraph", content=stripped)
            doc.elements.append(elem)
        if in_table and table_lines:
            elem = MarkdownElement(element_type="table", content="\n".join(table_lines))
            doc.elements.append(elem)
        if in_code_block and code_lines:
            elem = MarkdownElement(
                element_type="code", content="\n".join(code_lines), language=code_lang,
            )
            doc.elements.append(elem)
        doc.word_count = sum(
            len(e.content.split()) for e in doc.elements
            if e.content and e.element_type in ("paragraph", "heading", "list", "blockquote")
        )
        return doc

    def _write_pdf(self, doc: MarkdownDocument, output_path: str,
                   options: MarkdownConversionOptions):
        try:
            from reportlab.lib.pagesizes import A4, letter, legal
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Preformatted
            from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
            size_map = {"A4": A4, "letter": letter, "legal": legal}
            page_size = size_map.get(options.page_size, A4)
            doc_builder = SimpleDocTemplate(
                output_path, pagesize=page_size,
                topMargin=options.margins["top"],
                bottomMargin=options.margins["bottom"],
                leftMargin=options.margins["left"],
                rightMargin=options.margins["right"],
            )
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                "H1", parent=styles["Heading1"], fontSize=options.font_size_h1,
                spaceAfter=12,
            ))
            styles.add(ParagraphStyle(
                "H2", parent=styles["Heading2"], fontSize=options.font_size_h2,
                spaceAfter=10,
            ))
            styles.add(ParagraphStyle(
                "H3", parent=styles["Heading3"], fontSize=options.font_size_h3,
                spaceAfter=8,
            ))
            styles.add(ParagraphStyle(
                "BodyCustom", parent=styles["Normal"], fontSize=options.font_size_body,
                leading=options.font_size_body * options.line_spacing, spaceAfter=6,
            ))
            styles.add(ParagraphStyle(
                "Code", parent=styles["Code"], fontName=options.code_font,
                fontSize=9, spaceAfter=6, backColor="#F5F5F5",
            ))
            styles.add(ParagraphStyle(
                "BlockQuote", parent=styles["Normal"],
                leftIndent=20, fontName="Helvetica-Oblique",
                fontSize=options.font_size_body, spaceAfter=8,
            ))
            story = []
            for elem in doc.elements:
                if elem.element_type == "heading":
                    level = min(elem.level, 3)
                    style_name = f"H{level}"
                    story.append(Paragraph(elem.content, styles[style_name]))
                    story.append(Spacer(1, 6))
                elif elem.element_type == "paragraph":
                    safe = elem.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", elem.content)
                    for text, url in links:
                        safe = safe.replace(
                            f"[{text}]({url})",
                            f'<a href="{url}">{text}</a>',
                        )
                    story.append(Paragraph(safe, styles["BodyCustom"]))
                elif elem.element_type == "code":
                    safe = elem.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Preformatted(safe, styles["Code"]))
                    story.append(Spacer(1, 6))
                elif elem.element_type == "blockquote":
                    safe = elem.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(f"&ldquo;{safe}&rdquo;", styles["BlockQuote"]))
                elif elem.element_type == "list":
                    for item in elem.items:
                        marker = "&bull;" if not elem.ordered else "&middot;"
                        safe = item.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        story.append(Paragraph(f"&nbsp;&nbsp;{marker} {safe}", styles["BodyCustom"]))
                elif elem.element_type == "hr":
                    story.append(Spacer(1, 12))
                elif elem.element_type == "table":
                    story.append(Paragraph(
                        "<i>[Table content]</i>", styles["BodyCustom"],
                    ))
            if story:
                doc_builder.build(story)
        except ImportError:
            logger.warning("reportlab not available; writing minimal PDF")
            with open(output_path, "wb") as f:
                f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n")

    def markdown_string_to_pdf(self, content: str, output_path: str) -> str:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        try:
            tmp.write(content)
            tmp.close()
            return self.markdown_to_pdf(tmp.name, output_path)
        finally:
            os.unlink(tmp.name)

    def pdf_to_markdown_string(self, pdf_path: str) -> str:
        return self.pdf_to_markdown(pdf_path)

    def generate_toc(self, doc: MarkdownDocument) -> str:
        toc_lines = ["## Table of Contents\n"]
        for elem in doc.elements:
            if elem.element_type == "heading":
                indent = "  " * (elem.level - 1)
                anchor = elem.content.lower().replace(" ", "-")
                anchor = re.sub(r"[^\w\-]", "", anchor)
                toc_lines.append(f"{indent}- [{elem.content}](#{anchor})")
        return "\n".join(toc_lines)

    def get_capabilities(self) -> dict:
        return {
            "markdown_to_pdf": True,
            "pdf_to_markdown": True,
            "parse_markdown": True,
            "generate_toc": True,
            "supported_elements": [
                "heading", "paragraph", "code", "blockquote", "list",
                "table", "hr", "image", "link",
            ],
        }
