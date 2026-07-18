"""PPTX import: convert PowerPoint slides to PDF pages preserving layout, animations as static, and speaker notes."""

import io
import logging
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

PNS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


@dataclass
class TextShape:
    text: str = ""
    left_pt: float = 0
    top_pt: float = 0
    width_pt: float = 0
    height_pt: float = 0
    font_name: str = ""
    font_size_pt: float = 18.0
    bold: bool = False
    italic: bool = False
    color: str = ""
    alignment: str = "left"
    is_placeholder: bool = False
    placeholder_idx: int = -1
    placeholder_type: str = ""


@dataclass
class Picture:
    data: bytes = b""
    content_type: str = ""
    left_pt: float = 0
    top_pt: float = 0
    width_pt: float = 0
    height_pt: float = 0
    name: str = ""
    description: str = ""


@dataclass
class Shape:
    shape_type: str = ""
    left_pt: float = 0
    top_pt: float = 0
    width_pt: float = 0
    height_pt: float = 0
    fill_color: str = ""
    line_color: str = ""
    line_width_pt: float = 1.0
    is_group: bool = False
    group_shapes: list = field(default_factory=list)


@dataclass
class Animation:
    trigger: str = "onClick"
    effect_type: str = "appear"
    target_shape_idx: int = -1
    duration_ms: int = 500
    delay_ms: int = 0
    sequence: int = 0


@dataclass
class Slide:
    index: int = 0
    layout_name: str = ""
    text_shapes: list[TextShape] = field(default_factory=list)
    pictures: list[Picture] = field(default_factory=list)
    shapes: list[Shape] = field(default_factory=list)
    animations: list[Animation] = field(default_factory=list)
    speaker_notes: str = ""
    notes_slide_id: str = ""
    background_color: str = ""
    is_hidden: bool = False
    transition_type: str = ""
    transition_duration_ms: int = 500
    slide_width_pt: float = 720.0
    slide_height_pt: float = 540.0


@dataclass
class PPTXContent:
    slides: list[Slide] = field(default_factory=list)
    slide_width_pt: float = 720.0
    slide_height_pt: float = 540.0
    metadata: dict = field(default_factory=dict)
    slide_master_count: int = 1
    total_slides: int = 0
    author: str = ""
    title: str = ""
    subject: str = ""
    created: str = ""
    modified: str = ""


class PowerPointImporter:
    """Import PPTX presentations converting slides to static PDF pages with notes preservation."""

    def __init__(self):
        self._rels: dict[str, str] = {}
        self._media_parts: dict[str, bytes] = {}

    def import_file(self, file_path: str) -> PPTXContent:
        with zipfile.ZipFile(file_path, "r") as zf:
            return self._parse(zf)

    def import_bytes(self, data: bytes) -> PPTXContent:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            return self._parse(zf)

    def _parse(self, zf: zipfile.ZipFile) -> PPTXContent:
        content = PPTXContent()
        self._parse_relationships(zf)
        self._parse_media(zf)
        self._parse_presentation(zf, content)
        self._parse_metadata(zf, content)
        logger.info(f"Imported PPTX: {len(content.slides)} slides")
        return content

    def _parse_relationships(self, zf: zipfile.ZipFile):
        self._rels = {}
        for name in zf.namelist():
            if name.endswith(".rels"):
                rels_path = name
                base_dir = "/".join(rels_path.split("/")[:-1])
                try:
                    root = ET.fromstring(zf.read(rels_path))
                    for rel in root:
                        r_id = rel.get("Id", "")
                        target = rel.get("Target", "")
                        if base_dir:
                            target = f"{base_dir}/{target}"
                        self._rels[r_id] = target
                except ET.ParseError:
                    continue

    def _parse_media(self, zf: zipfile.ZipFile):
        self._media_parts = {}
        for name in zf.namelist():
            if "media/" in name and not name.endswith("/"):
                self._media_parts[name] = zf.read(name)

    def _parse_presentation(self, zf: zipfile.ZipFile, content: PPTXContent):
        pres_path = "ppt/presentation.xml"
        if pres_path not in zf.namelist():
            return
        root = ET.fromstring(zf.read(pres_path))
        sld_sz = root.find(f"{{{PNS['p']}}}sldSz")
        if sld_sz is not None:
            try:
                content.slide_width_pt = int(sld_sz.get("cx", "12192000")) / 12700.0
                content.slide_height_pt = int(sld_sz.get("cy", "6858000")) / 12700.0
            except (ValueError, TypeError):
                pass
        sld_id_lst = root.find(f"{{{PNS['p']}}}sldIdLst")
        if sld_id_lst is None:
            return
        pres_rels_path = "ppt/_rels/presentation.xml.rels"
        pres_rels = {}
        if pres_rels_path in zf.namelist():
            rels_root = ET.fromstring(zf.read(pres_rels_path))
            for rel in rels_root:
                r_id = rel.get("Id", "")
                target = rel.get("Target", "")
                pres_rels[r_id] = f"ppt/{target}" if not target.startswith("/") else target

        for idx, sld_id in enumerate(sld_id_lst.findall(f"{{{PNS['p']}}}sldId")):
            r_id = sld_id.get(f"{{{PNS['r']}}}id", "")
            slide_path = pres_rels.get(r_id, "")
            if slide_path and slide_path in zf.namelist():
                slide = self._parse_slide(zf, slide_path, idx, content)
                content.slides.append(slide)
        content.total_slides = len(content.slides)

    def _parse_slide(self, zf: zipfile.ZipFile, path: str, index: int, content: PPTXContent) -> Slide:
        slide = Slide(
            index=index, slide_width_pt=content.slide_width_pt,
            slide_height_pt=content.slide_height_pt,
        )
        root = ET.fromstring(zf.read(path))
        c_sld = root.find(f"{{{PNS['p']}}}cSld")
        if c_sld is None:
            return slide
        sp_tree = c_sld.find(f"{{{PNS['p']}}}spTree")
        if sp_tree is None:
            return slide
        shape_idx = 0
        for child in sp_tree:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "sp":
                text_shape = self._parse_text_shape(child)
                if text_shape:
                    slide.text_shapes.append(text_shape)
                    shape_idx += 1
            elif tag == "pic":
                picture = self._parse_picture(child)
                if picture:
                    slide.pictures.append(picture)
                    shape_idx += 1
            elif tag == "grpSp":
                group = self._parse_group_shape(child)
                slide.shapes.append(group)
                shape_idx += 1
            elif tag == "cxnSp":
                shape = self._parse_connector(child)
                if shape:
                    slide.shapes.append(shape)
            elif tag == "graphicFrame":
                ts = TextShape()
                ts.text = "[Chart/Table]"
                ts.is_placeholder = True
                slide.text_shapes.append(ts)
        self._parse_slide_animations(root, slide)
        self._parse_transition(root, slide)
        return slide

    def _parse_text_shape(self, elem) -> Optional[TextShape]:
        ts = TextShape()
        sp_pr = elem.find(f"{{{PNS['p']}}}spPr")
        nv_sp_pr = elem.find(f"{{{PNS['p']}}}nvSpPr")
        if nv_sp_pr is not None:
            nv_pr = nv_sp_pr.find(f"{{{PNS['p']}}}nvPr")
            if nv_pr is not None:
                ph = nv_pr.find(f"{{{PNS['p']}}}ph")
                if ph is not None:
                    ts.is_placeholder = True
                    ts.placeholder_type = ph.get("type", "")
                    idx = ph.get("idx", "-1")
                    try:
                        ts.placeholder_idx = int(idx)
                    except (ValueError, TypeError):
                        pass
        if sp_pr is not None:
            xfrm = sp_pr.find(f"{{{PNS['a']}}}xfrm")
            if xfrm is not None:
                off = xfrm.find(f"{{{PNS['a']}}}off")
                ext = xfrm.find(f"{{{PNS['a']}}}ext")
                if off is not None:
                    try:
                        ts.left_pt = int(off.get("x", "0")) / 12700.0
                        ts.top_pt = int(off.get("y", "0")) / 12700.0
                    except (ValueError, TypeError):
                        pass
                if ext is not None:
                    try:
                        ts.width_pt = int(ext.get("cx", "0")) / 12700.0
                        ts.height_pt = int(ext.get("cy", "0")) / 12700.0
                    except (ValueError, TypeError):
                        pass
            solid_fill = sp_pr.find(f"{{{PNS['a']}}}solidFill")
            if solid_fill is not None:
                srgb = solid_fill.find(f"{{{PNS['a']}}}srgbClr")
                if srgb is not None:
                    ts.color = srgb.get("val", "")
        tx_body = elem.find(f"{{{PNS['a']}}}txBody")
        if tx_body is None:
            tx_body = elem.find(f"{{{PNS['p']}}}txBody")
        if tx_body is None:
            return ts if ts.is_placeholder else None
        text_parts = []
        for p in tx_body.findall(f"{{{PNS['a']}}}p"):
            for r in p.findall(f"{{{PNS['a']}}}r"):
                t = r.find(f"{{{PNS['a']}}}t")
                if t is not None and t.text:
                    text_parts.append(t.text)
                    rpr = r.find(f"{{{PNS['a']}}}rPr")
                    if rpr is not None:
                        if rpr.get("b", "0") == "1":
                            ts.bold = True
                        if rpr.get("i", "0") == "1":
                            ts.italic = True
                        sz = rpr.get("sz")
                        if sz:
                            try:
                                ts.font_size_pt = int(sz) / 100.0
                            except (ValueError, TypeError):
                                pass
                        alt_font = rpr.find(f"{{{PNS['a']}}}latin")
                        if alt_font is not None:
                            ts.font_name = alt_font.get("typeface", "")
            for br in p.findall(f"{{{PNS['a']}}}br"):
                text_parts.append("\n")
            ppr = p.find(f"{{{PNS['a']}}}pPr")
            if ppr is not None:
                algn = ppr.get("algn", "")
                if algn:
                    ts.alignment = algn
        ts.text = "".join(text_parts)
        return ts

    def _parse_picture(self, elem) -> Optional[Picture]:
        pic = Picture()
        pic_pr = elem.find(f"{{{PNS['p']}}}picPr")
        sp_pr = elem.find(f"{{{PNS['p']}}}spPr")
        nv_sp_pr = elem.find(f"{{{PNS['p']}}}nvPicPr")
        if nv_sp_pr is not None:
            c_nv_pr = nv_sp_pr.find(f"{{{PNS['p']}}}cNvPr")
            if c_nv_pr is not None:
                pic.name = c_nv_pr.get("name", "")
                pic.description = c_nv_pr.get("descr", "")
        if sp_pr is not None:
            xfrm = sp_pr.find(f"{{{PNS['a']}}}xfrm")
            if xfrm is not None:
                off = xfrm.find(f"{{{PNS['a']}}}off")
                ext = xfrm.find(f"{{{PNS['a']}}}ext")
                if off is not None:
                    try:
                        pic.left_pt = int(off.get("x", "0")) / 12700.0
                        pic.top_pt = int(off.get("y", "0")) / 12700.0
                    except (ValueError, TypeError):
                        pass
                if ext is not None:
                    try:
                        pic.width_pt = int(ext.get("cx", "0")) / 12700.0
                        pic.height_pt = int(ext.get("cy", "0")) / 12700.0
                    except (ValueError, TypeError):
                        pass
        blip_fill = elem.find(f".//{{{PNS['p']}}}blipFill") or elem.find(f".//{{{PNS['a']}}}blipFill")
        if blip_fill is not None:
            blip = blip_find = None
            for b in blip_fill.iter(f"{{{PNS['a']}}}blip"):
                blip = b
                break
            if blip is not None:
                r_embed = blip.get(f"{{{PNS['r']}}}embed", "")
                if r_embed and r_embed in self._rels:
                    media_path = self._rels[r_embed]
                    if media_path in self._media_parts:
                        pic.data = self._media_parts[media_path]
                        ext = media_path.rsplit(".", 1)[-1].lower()
                        pic.content_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"
        return pic if (pic.data or pic.name) else None

    def _parse_group_shape(self, elem) -> Shape:
        shape = Shape(shape_type="group")
        sp_pr = elem.find(f"{{{PNS['p']}}}spPr")
        if sp_pr is not None:
            xfrm = sp_pr.find(f"{{{PNS['a']}}}xfrm")
            if xfrm is not None:
                off = xfrm.find(f"{{{PNS['a']}}}off")
                ext = xfrm.find(f"{{{PNS['a']}}}ext")
                if off is not None:
                    try:
                        shape.left_pt = int(off.get("x", "0")) / 12700.0
                        shape.top_pt = int(off.get("y", "0")) / 12700.0
                    except (ValueError, TypeError):
                        pass
                if ext is not None:
                    try:
                        shape.width_pt = int(ext.get("cx", "0")) / 12700.0
                        shape.height_pt = int(ext.get("cy", "0")) / 12700.0
                    except (ValueError, TypeError):
                        pass
        shape.is_group = True
        return shape

    def _parse_connector(self, elem) -> Optional[Shape]:
        shape = Shape(shape_type="connector")
        sp_pr = elem.find(f"{{{PNS['p']}}}spPr")
        if sp_pr is not None:
            xfrm = sp_pr.find(f"{{{PNS['a']}}}xfrm")
            if xfrm is not None:
                off = xfrm.find(f"{{{PNS['a']}}}off")
                ext = xfrm.find(f"{{{PNS['a']}}}ext")
                if off is not None:
                    try:
                        shape.left_pt = int(off.get("x", "0")) / 12700.0
                        shape.top_pt = int(off.get("y", "0")) / 12700.0
                    except (ValueError, TypeError):
                        pass
                if ext is not None:
                    try:
                        shape.width_pt = int(ext.get("cx", "0")) / 12700.0
                        shape.height_pt = int(ext.get("cy", "0")) / 12700.0
                    except (ValueError, TypeError):
                        pass
        return shape

    def _parse_slide_animations(self, root: ET.Element, slide: Slide):
        timing = root.find(f"{{{PNS['p']}}}timing")
        if timing is None:
            return
        tn_lst = timing.find(f"{{{PNS['p']}}}tnLst")
        if tn_lst is None:
            return
        seq = 0
        for par in tn_lst.iter(f"{{{PNS['p']}}}par"):
            for c_tn in par.iter(f"{{{PNS['p']}}}cTn"):
                preset_class = c_tn.get("presetClass", "")
                preset_id = c_tn.get("presetID", "")
                dur = c_tn.get("dur", "500")
                anim = Animation(
                    trigger="onClick" if preset_class == "entr" else "withPrevious",
                    effect_type=preset_id or "appear",
                    duration_ms=int(dur) if dur.isdigit() else 500,
                    sequence=seq,
                )
                slide.animations.append(anim)
            seq += 1

    def _parse_transition(self, root: ET.Element, slide: Slide):
        transition = root.find(f"{{{PNS['p']}}}transition")
        if transition is None:
            return
        for attr in ["advClick", "advTm"]:
            val = transition.get(attr, "")
            if val and val.isdigit():
                slide.transition_duration_ms = int(val)
        slide.transition_type = transition.tag.split("}")[-1] if "}" in transition.tag else "none"

    def _parse_notes_slide(self, zf: zipfile.ZipFile, notes_path: str) -> str:
        if notes_path not in zf.namelist():
            return ""
        root = ET.fromstring(zf.read(notes_path))
        notes_body = root.find(f".//{{{PNS['p']}}}txBody")
        if notes_body is None:
            return ""
        parts = []
        for p in notes_body.findall(f"{{{PNS['a']}}}p"):
            for r in p.findall(f"{{{PNS['a']}}}r"):
                t = r.find(f"{{{PNS['a']}}}t")
                if t is not None and t.text:
                    parts.append(t.text)
        return "\n".join(parts)

    def _parse_metadata(self, zf: zipfile.ZipFile, content: PPTXContent):
        core_path = "docProps/core.xml"
        if core_path in zf.namelist():
            root = ET.fromstring(zf.read(core_path))
            for child in root:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child.text:
                    content.metadata[tag] = child.text
                    if tag == "creator":
                        content.author = child.text
                    elif tag == "title":
                        content.title = child.text
                    elif tag == "subject":
                        content.subject = child.text
                    elif tag == "created":
                        content.created = child.text
                    elif tag == "modified":
                        content.modified = child.text
