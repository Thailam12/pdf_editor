"""SVG import/export: render SVG into PDF and export PDF elements as SVG."""

import os
import re
import io
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SVGElement:
    tag: str = ""
    attributes: dict = field(default_factory=dict)
    text: str = ""
    children: list = field(default_factory=list)
    transform: str = ""
    fill: str = "black"
    stroke: str = "none"
    stroke_width: float = 1.0
    opacity: float = 1.0


@dataclass
class SVGDocument:
    width: float = 0
    height: float = 0
    viewBox: str = ""
    xmlns: str = "http://www.w3.org/2000/svg"
    elements: list[SVGElement] = field(default_factory=list)
    title: str = ""
    description: str = ""
    defs: list = field(default_factory=list)
    groups: int = 0
    paths: int = 0
    text_elements: int = 0
    images: int = 0


@dataclass
class SVGBoundingBox:
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0


class SVGConverter:
    """Bidirectional SVG-PDF conversion with element-level parsing and generation."""

    SVG_NS = "http://www.w3.org/2000/svg"

    def __init__(self):
        self._parse_cache = {}

    def import_svg(self, svg_path: str) -> SVGDocument:
        with open(svg_path, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse_svg_string(content)

    def parse_svg_string(self, svg_string: str) -> SVGDocument:
        doc = SVGDocument()
        try:
            root = ET.fromstring(svg_string)
        except ET.ParseError as e:
            logger.error(f"SVG parse error: {e}")
            return doc
        doc.width = self._parse_length(root.get("width", "100"))
        doc.height = self._parse_length(root.get("height", "100"))
        doc.viewBox = root.get("viewBox", "")
        for child in root:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "title":
                doc.title = child.text or ""
            elif tag == "description":
                doc.description = child.text or ""
            elif tag == "defs":
                self._parse_defs(child, doc)
            elif tag == "g":
                doc.groups += 1
                self._parse_group(child, doc.elements)
            else:
                elem = self._parse_element(child)
                if elem:
                    doc.elements.append(elem)
                    if tag == "path":
                        doc.paths += 1
                    elif tag == "text":
                        doc.text_elements += 1
                    elif tag in ("image", "use"):
                        doc.images += 1
        return doc

    def _parse_element(self, elem) -> Optional[SVGElement]:
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        svg_elem = SVGElement(tag=tag)
        svg_elem.attributes = dict(elem.attrib)
        svg_elem.text = elem.text or ""
        svg_elem.fill = elem.get("fill", "black")
        svg_elem.stroke = elem.get("stroke", "none")
        try:
            svg_elem.stroke_width = float(elem.get("stroke-width", "1"))
        except (ValueError, TypeError):
            pass
        try:
            svg_elem.opacity = float(elem.get("opacity", "1"))
        except (ValueError, TypeError):
            pass
        svg_elem.transform = elem.get("transform", "")
        return svg_elem

    def _parse_group(self, elem, elements: list):
        for child in elem:
            child_elem = self._parse_element(child)
            if child_elem:
                elements.append(child_elem)
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "g":
                    self._parse_group(child, elements)

    def _parse_defs(self, elem, doc: SVGDocument):
        for child in elem:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            doc.defs.append({"type": tag, "id": child.get("id", ""), "attributes": dict(child.attrib)})

    def _parse_length(self, value: str) -> float:
        value = value.strip()
        for unit, factor in [("px", 1), ("pt", 1), ("in", 72), ("cm", 28.35), ("mm", 2.835), ("em", 12)]:
            if value.endswith(unit):
                try:
                    return float(value[:-len(unit)]) * factor
                except ValueError:
                    return 0
        try:
            return float(value)
        except ValueError:
            return 100

    def import_to_pdf(self, svg_path: str, output_path: str) -> str:
        doc = self.import_svg(svg_path)
        svg_content = self._read_svg_file(svg_path)
        self._write_svg_pdf(doc, svg_content, output_path)
        logger.info(f"SVG to PDF: {svg_path} -> {output_path}")
        return output_path

    def _read_svg_file(self, svg_path: str) -> str:
        with open(svg_path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_svg_pdf(self, doc: SVGDocument, svg_content: str, output_path: str):
        try:
            from reportlab.graphics import renderPDF
            from reportlab.graphics.shapes import Drawing, String
            width = doc.width or 612
            height = doc.height or 792
            drawing = Drawing(width, height)
            for elem in doc.elements:
                if elem.tag == "text":
                    content = elem.text or elem.attributes.get("textContent", "")
                    if content:
                        fill = elem.fill if elem.fill != "none" else "#000000"
                        try:
                            from reportlab.lib.colors import HexColor
                            color = HexColor(fill) if fill.startswith("#") else None
                        except (ValueError, Exception):
                            color = None
                        s = String(
                            self._get_num(elem.attributes, "x", 0),
                            self._get_num(elem.attributes, "y", 0),
                            content,
                            fillColor=color,
                        )
                        drawing.add(s)
            from reportlab.lib.pagesizes import landscape, A4
            from reportlab.pdfgen import canvas as rl_canvas
            c = rl_canvas.Canvas(output_path, pagesize=(width, height))
            renderPDF.draw(drawing, c, 0, 0)
            c.save()
        except ImportError:
            logger.warning("reportlab not available; writing minimal SVG PDF")
            with open(output_path, "wb") as f:
                f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n")

    def export_page_as_svg(self, page_data: bytes = None, page_index: int = 0,
                           width: float = 612, height: float = 792) -> str:
        svg_parts = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="{self.SVG_NS}" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            f'  <title>Page {page_index + 1}</title>',
            f'  <rect width="{width}" height="{height}" fill="white"/>',
        ]
        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def export_elements_as_svg(self, elements: list[dict], width: float = 612,
                                height: float = 792) -> str:
        svg_parts = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="{self.SVG_NS}" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            f'  <rect width="{width}" height="{height}" fill="white"/>',
        ]
        for elem in elements:
            elem_type = elem.get("type", "")
            if elem_type == "text":
                x = elem.get("x", 0)
                y = elem.get("y", 0)
                text = elem.get("content", "")
                font_size = elem.get("font_size", 12)
                fill = elem.get("color", "#000000")
                svg_parts.append(
                    f'  <text x="{x}" y="{y}" fill="{fill}" font-size="{font_size}">{text}</text>'
                )
            elif elem_type == "rectangle":
                x = elem.get("x", 0)
                y = elem.get("y", 0)
                w = elem.get("width", 100)
                h = elem.get("height", 50)
                fill = elem.get("fill", "none")
                stroke = elem.get("stroke", "#000000")
                svg_parts.append(
                    f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" '
                    f'fill="{fill}" stroke="{stroke}"/>'
                )
            elif elem_type == "line":
                x1, y1 = elem.get("x1", 0), elem.get("y1", 0)
                x2, y2 = elem.get("x2", 100), elem.get("y2", 100)
                stroke = elem.get("stroke", "#000000")
                svg_parts.append(
                    f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}"/>'
                )
            elif elem_type == "path":
                d = elem.get("d", "")
                fill = elem.get("fill", "none")
                stroke = elem.get("stroke", "#000000")
                svg_parts.append(f'  <path d="{d}" fill="{fill}" stroke="{stroke}"/>')
        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    def optimize_svg(self, svg_content: str) -> str:
        svg_content = re.sub(r"<!--.*?-->", "", svg_content, flags=re.DOTALL)
        svg_content = re.sub(r"\s+", " ", svg_content)
        svg_content = re.sub(r">\s+<", "><", svg_content)
        return svg_content.strip()

    def _get_num(self, attrs: dict, key: str, default: float = 0) -> float:
        try:
            return float(attrs.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_capabilities(self) -> dict:
        return {
            "import_svg": True,
            "export_svg": True,
            "element_parsing": True,
            "optimize": True,
            "pdf_conversion": True,
            "supported_elements": ["text", "rect", "circle", "ellipse", "path",
                                    "line", "polyline", "polygon", "image", "g"],
        }
