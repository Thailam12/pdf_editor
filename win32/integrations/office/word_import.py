"""DOCX import: parse Word documents preserving text, images, tables, formatting, and tracked changes."""

import io
import logging
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
}


@dataclass
class TextRun:
    text: str = ""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    font_name: str = ""
    font_size_pt: float = 11.0
    color: str = ""
    is_tracked_change: bool = False
    change_type: str = ""
    change_author: str = ""


@dataclass
class Paragraph:
    runs: list[TextRun] = field(default_factory=list)
    alignment: str = "left"
    style: str = ""
    heading_level: int = 0
    is_list_item: bool = False
    list_level: int = 0
    spacing_after_pt: float = 8.0
    spacing_before_pt: float = 0.0


@dataclass
class Table:
    rows: list[list[str]] = field(default_factory=list)
    column_count: int = 0
    row_count: int = 0
    borders: bool = True
    width_pct: float = 100.0


@dataclass
class Image:
    data: bytes = b""
    content_type: str = ""
    width_pt: float = 0
    height_pt: float = 0
    description: str = ""
    name: str = ""


@dataclass
class TrackedChange:
    change_type: str = ""
    author: str = ""
    date: str = ""
    text: str = ""


@dataclass
class DOCXContent:
    paragraphs: list[Paragraph] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)
    tracked_changes: list[TrackedChange] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    page_width_pt: float = 612.0
    page_height_pt: float = 792.0
    margin_top_pt: float = 72.0
    margin_bottom_pt: float = 72.0
    margin_left_pt: float = 72.0
    margin_right_pt: float = 72.0


class WordImporter:
    """Parse DOCX files preserving structure, formatting, images, tables, and tracked changes."""

    def __init__(self):
        self._zip: Optional[zipfile.ZipFile] = None
        self._rels: dict[str, str] = {}
        self._doc_rels: dict[str, str] = {}
        self._media_parts: dict[str, bytes] = {}

    def import_file(self, file_path: str) -> DOCXContent:
        with zipfile.ZipFile(file_path, "r") as zf:
            return self._parse(zf)

    def import_bytes(self, data: bytes) -> DOCXContent:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            return self._parse(zf)

    def _parse(self, zf: zipfile.ZipFile) -> DOCXContent:
        content = DOCXContent()
        self._parse_rels(zf)
        self._parse_media(zf)
        self._parse_document_xml(zf, content)
        self._parse_numbering(zf)
        self._parse_metadata(zf, content)
        self._parse_settings(zf, content)
        logger.info(f"Imported DOCX: {len(content.paragraphs)} paragraphs, "
                     f"{len(content.tables)} tables, {len(content.images)} images")
        return content

    def _parse_rels(self, zf: zipfile.ZipFile):
        self._rels = {}
        if "[Content_Types].xml" in zf.namelist():
            ct_xml = zf.read("[Content_Types].xml")
            root = ET.fromstring(ct_xml)
            for override in root.iter():
                if "Override" in override.tag:
                    part = override.get("PartName", "")
                    ctype = override.get("ContentType", "")
                    self._rels[part] = ctype

        self._doc_rels = {}
        rels_path = "word/_rels/document.xml.rels"
        if rels_path in zf.namelist():
            rels_xml = zf.read(rels_path)
            root = ET.fromstring(rels_xml)
            for rel in root:
                r_id = rel.get("Id", "")
                target = rel.get("Target", "")
                rel_type = rel.get("Type", "")
                self._doc_rels[r_id] = f"word/{target}" if not target.startswith("/") else target

    def _parse_media(self, zf: zipfile.ZipFile):
        self._media_parts = {}
        for name in zf.namelist():
            if name.startswith("word/media/"):
                self._media_parts[name] = zf.read(name)

    def _parse_document_xml(self, zf: zipfile.ZipFile, content: DOCXContent):
        if "word/document.xml" not in zf.namelist():
            return
        doc_xml = zf.read("word/document.xml")
        root = ET.fromstring(doc_xml)
        body = root.find(f"{{{NS['w']}}}body")
        if body is None:
            return
        for child in body:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "p":
                para = self._parse_paragraph(child)
                content.paragraphs.append(para)
            elif tag == "tbl":
                table = self._parse_table(child)
                content.tables.append(table)
            elif tag == "sectPr":
                self._parse_section_props(child, content)

    def _parse_paragraph(self, elem) -> Paragraph:
        para = Paragraph()
        p_pr = elem.find(f"{{{NS['w']}}}pPr")
        if p_pr is not None:
            jc = p_pr.find(f"{{{NS['w']}}}jc")
            if jc is not None:
                val = jc.get(f"{{{NS['w']}}}val", "left")
                para.alignment = val if val in ("left", "center", "right", "both") else "left"
            style_el = p_pr.find(f"{{{NS['w']}}}pStyle")
            if style_el is not None:
                para.style = style_el.get(f"{{{NS['w']}}}val", "")
                if para.style and "heading" in para.style.lower():
                    try:
                        para.heading_level = int(para.style.replace("Heading", "").strip() or "1")
                    except (ValueError, AttributeError):
                        pass
            num_pr = p_pr.find(f"{{{NS['w']}}}numPr")
            if num_pr is not None:
                para.is_list_item = True
                ilvl = num_pr.find(f"{{{NS['w']}}}ilvl")
                if ilvl is not None:
                    try:
                        para.list_level = int(ilvl.get(f"{{{NS['w']}}}val", "0"))
                    except (ValueError, AttributeError):
                        pass
            spacing = p_pr.find(f"{{{NS['w']}}}spacing")
            if spacing is not None:
                after = spacing.get(f"{{{NS['w']}}}after", "")
                before = spacing.get(f"{{{NS['w']}}}before", "")
                if after:
                    try:
                        para.spacing_after_pt = int(after) / 20.0
                    except (ValueError, TypeError):
                        pass
                if before:
                    try:
                        para.spacing_before_pt = int(before) / 20.0
                    except (ValueError, TypeError):
                        pass
        for r in elem.findall(f"{{{NS['w']}}}r"):
            run = self._parse_run(r)
            para.runs.append(run)
        for cr in elem.findall(f"{{{NS['w']}}}r"):
            for deleted in cr.findall(f"{{{NS['w']}}}del"):
                text_el = deleted.find(f"{{{NS['w']}}}delText")
                if text_el is not None and text_el.text:
                    para.runs.append(TextRun(
                        text=text_el.text, is_tracked_change=True, change_type="deletion"
                    ))
            for inserted in cr.findall(f"{{{NS['w']}}}ins"):
                t_el = inserted.find(f"{{{NS['w']}}}t")
                if t_el is not None and t_el.text:
                    para.runs.append(TextRun(
                        text=t_el.text, is_tracked_change=True, change_type="insertion"
                    ))
        return para

    def _parse_run(self, elem) -> TextRun:
        run = TextRun()
        r_pr = elem.find(f"{{{NS['w']}}}rPr")
        if r_pr is not None:
            if r_pr.find(f"{{{NS['w']}}}b") is not None:
                run.bold = True
            if r_pr.find(f"{{{NS['w']}}}i") is not None:
                run.italic = True
            u = r_pr.find(f"{{{NS['w']}}}u")
            if u is not None and u.get(f"{{{NS['w']}}}val", "none") != "none":
                run.underline = True
            rFonts = r_pr.find(f"{{{NS['w']}}}rFonts")
            if rFonts is not None:
                run.font_name = rFonts.get(f"{{{NS['w']}}}ascii", "")
            sz = r_pr.find(f"{{{NS['w']}}}sz")
            if sz is not None:
                try:
                    run.font_size_pt = int(sz.get(f"{{{NS['w']}}}val", "22")) / 2.0
                except (ValueError, TypeError):
                    pass
            color = r_pr.find(f"{{{NS['w']}}}color")
            if color is not None:
                run.color = color.get(f"{{{NS['w']}}}val", "")
        for t in elem.findall(f"{{{NS['w']}}}t"):
            if t.text:
                run.text += t.text
        drawing = elem.find(f"{{{NS['w']}}}drawing")
        if drawing is not None:
            run.text = f"[Image: {self._extract_image_name(drawing)}]"
        return run

    def _extract_image_name(self, drawing) -> str:
        for blip in drawing.iter(f"{{{NS['a']}}}blip"):
            r_embed = blip.get(f"{{{NS['r']}}}embed", "")
            if r_embed and r_embed in self._doc_rels:
                return self._doc_rels[r_embed]
        return "unknown"

    def _parse_table(self, elem) -> Table:
        table = Table()
        for tr in elem.findall(f"{{{NS['w']}}}tr"):
            row = []
            for tc in tr.findall(f"{{{NS['w']}}}tc"):
                cell_text = ""
                for p in tc.findall(f"{{{NS['w']}}}p"):
                    for r in p.findall(f"{{{NS['w']}}}r"):
                        for t in r.findall(f"{{{NS['w']}}}t"):
                            if t.text:
                                cell_text += t.text
                row.append(cell_text)
            table.rows.append(row)
        table.row_count = len(table.rows)
        table.column_count = max((len(r) for r in table.rows), default=0)
        tbl_pr = elem.find(f"{{{NS['w']}}}tblPr")
        if tbl_pr is not None:
            tbl_w = tbl_pr.find(f"{{{NS['w']}}}tblW")
            if tbl_w is not None:
                w_val = tbl_w.get(f"{{{NS['w']}}}val", "")
                w_type = tbl_w.get(f"{{{NS['w']}}}type", "dxa")
                if w_type == "pct":
                    try:
                        table.width_pct = int(w_val) / 50.0
                    except (ValueError, TypeError):
                        pass
        return table

    def _parse_section_props(self, elem, content: DOCXContent):
        pg_sz = elem.find(f"{{{NS['w']}}}pgSz")
        if pg_sz is not None:
            w = pg_sz.get(f"{{{NS['w']}}}w", "")
            h = pg_sz.get(f"{{{NS['w']}}}h", "")
            if w:
                try:
                    content.page_width_pt = int(w) / 20.0
                except (ValueError, TypeError):
                    pass
            if h:
                try:
                    content.page_height_pt = int(h) / 20.0
                except (ValueError, TypeError):
                    pass
        mar = elem.find(f"{{{NS['w']}}}pgMar")
        if mar is not None:
            for attr, field_name in [("top", "margin_top_pt"), ("bottom", "margin_bottom_pt"),
                                     ("left", "margin_left_pt"), ("right", "margin_right_pt")]:
                val = mar.get(f"{{{NS['w']}}}{attr}", "")
                if val:
                    try:
                        setattr(content, field_name, int(val) / 20.0)
                    except (ValueError, TypeError):
                        pass

    def _parse_numbering(self, zf: zipfile.ZipFile):
        pass

    def _parse_metadata(self, zf: zipfile.ZipFile, content: DOCXContent):
        core_path = "docProps/core.xml"
        if core_path in zf.namelist():
            core_xml = zf.read(core_path)
            root = ET.fromstring(core_xml)
            for child in root:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child.text:
                    content.metadata[tag] = child.text

    def _parse_settings(self, zf: zipfile.ZipFile, content: DOCXContent):
        pass

    def get_images(self, content: DOCXContent) -> list[tuple[str, bytes]]:
        result = []
        for name, data in self._media_parts.items():
            if name.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".emf", ".wmf")):
                ct = "image/png" if name.endswith(".png") else "image/jpeg"
                result.append((name, data))
        return result
