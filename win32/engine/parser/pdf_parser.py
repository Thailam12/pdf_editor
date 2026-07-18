"""Full PDF parser using PyMuPDF (fitz) as the backend.

Reads any PDF and produces a :class:`PDFDocument` intermediate-representation
that the rest of the engine can consume.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import fitz

from .content_stream import ContentStreamDecoder
from .font_handler import FontHandler
from .object_model import (
    AnnotationType,
    ContentBlock,
    EncryptionMethod,
    ExtGState,
    FormFieldType,
    ImageBlock,
    ObjectType,
    PageBoxes,
    PDFAnnotation,
    PDFAttachment,
    PDFColorSpace,
    PDFDocument,
    PDFFormField,
    PDFFont,
    PDFMarkInfo,
    PDFMetadata,
    PDFOutputIntent,
    PDFPage,
    PDFPattern,
    PDFResource,
    PDFSignature,
    PDFStructureElement,
    PDFThread,
    PDFThreadBead,
    PDFBookmark,
)


# ---------------------------------------------------------------------------
# Annotation-type mapping
# ---------------------------------------------------------------------------

_ANNOT_MAP: Dict[str, AnnotationType] = {
    "Text": AnnotationType.TEXT,
    "Link": AnnotationType.LINK,
    "FreeText": AnnotationType.FREE_TEXT,
    "Line": AnnotationType.LINE,
    "Square": AnnotationType.SQUARE,
    "Circle": AnnotationType.CIRCLE,
    "Polygon": AnnotationType.POLYGON,
    "PolyLine": AnnotationType.POLY_LINE,
    "Highlight": AnnotationType.HIGHLIGHT,
    "Underline": AnnotationType.UNDERLINE,
    "Squiggly": AnnotationType.SQUIGGLY,
    "StrikeOut": AnnotationType.STRIKEOUT,
    "Stamp": AnnotationType.STAMP,
    "Caret": AnnotationType.CARET,
    "Ink": AnnotationType.INK,
    "Popup": AnnotationType.POPUP,
    "FileAttachment": AnnotationType.FILE_ATTACHMENT,
    "Sound": AnnotationType.SOUND,
    "Movie": AnnotationType.MOVIE,
    "Widget": AnnotationType.WIDGET,
    "Screen": AnnotationType.SCREEN,
    "3D": AnnotationType.D_3D,  # noqa: enum alias
    "Redact": AnnotationType.REDACT,
    "Projection": AnnotationType.PROJECTION,
    "RichMedia": AnnotationType.RICH_MEDIA,
}


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

class PDFParser:
    """Parse a PDF file and return a :class:`PDFDocument` IR.

    Usage::

        parser = PDFParser()
        doc = parser.parse("path/to/file.pdf")
        print(doc.metadata.title)
    """

    def __init__(self, password: str = "") -> None:
        self._password = password

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, path: str) -> PDFDocument:
        """Parse *path* and return a fully-populated :class:`PDFDocument`."""
        doc = PDFDocument(file_path=path)

        fitz_doc = fitz.open(path)
        try:
            doc.version = self._get_version(fitz_doc)
            doc.page_count = fitz_doc.page_count
            self._parse_encryption(fitz_doc, doc)
            self._parse_metadata(fitz_doc, doc)
            self._parse_fonts(fitz_doc, doc)
            self._parse_pages(fitz_doc, doc)
            self._parse_bookmarks(fitz_doc, doc)
            self._parse_attachments(fitz_doc, doc)
            self._parse_form_fields(fitz_doc, doc)
            self._parse_signatures(fitz_doc, doc)
            self._parse_global_annotations(fitz_doc, doc)
            self._parse_output_intents(fitz_doc, doc)
            self._parse_threads(fitz_doc, doc)
            self._parse_structure_tree(fitz_doc, doc)
            self._parse_mark_info(fitz_doc, doc)
        finally:
            fitz_doc.close()

        return doc

    # ------------------------------------------------------------------
    # Version
    # ------------------------------------------------------------------

    @staticmethod
    def _get_version(fitz_doc: fitz.Document) -> str:
        try:
            meta = fitz_doc.metadata
            pdf_version = meta.get("format", "")
            if pdf_version:
                return pdf_version
        except Exception:
            pass
        # Fallback: read header
        try:
            raw = fitz_doc.tobytes(garbage=0, deflate=False)[:32]
            text = raw.decode("latin-1", errors="replace")
            m = re.search(r"%PDF-(\d+\.\d+)", text)
            if m:
                return m.group(1)
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------------
    # Encryption
    # ------------------------------------------------------------------

    def _parse_encryption(self, fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        enc = doc.encryption
        try:
            is_encrypted = fitz_doc.is_encrypted
            if not is_encrypted:
                enc.method = EncryptionMethod.NONE
                return
        except Exception:
            enc.method = EncryptionMethod.UNKNOWN
            return

        # Determine permissions
        try:
            enc.permissions = fitz_doc.permissions
        except Exception:
            pass

        # Try to detect the encryption method from the raw trailer
        try:
            xref_len = fitz_doc.xref_length()
            for xref in range(1, min(xref_len, 5)):
                try:
                    obj = fitz_doc.xref_object(xref, compressed=False)
                except Exception:
                    continue
                if "/Encrypt" not in obj:
                    continue
                enc_ref = re.search(r"/Encrypt\s+(\d+)\s+\d+\s+R", obj)
                if not enc_ref:
                    continue
                enc_xref = int(enc_ref.group(1))
                try:
                    enc_obj = fitz_doc.xref_object(enc_xref, compressed=False)
                except Exception:
                    continue

                v = re.search(r"/V\s+(\d+)", enc_obj)
                r = re.search(r"/R\s+(\d+)", enc_obj)
                length = re.search(r"/Length\s+(\d+)", enc_obj)

                version = int(v.group(1)) if v else 0
                revision = int(r.group(1)) if r else 0
                key_len = int(length.group(1)) if length else 0

                enc.version = version
                enc.revision = revision
                enc.key_length = key_len

                if version == 1 and revision == 2:
                    enc.method = EncryptionMethod.RC4_40
                    enc.algorithm = "RC4"
                elif version == 2 and revision == 3:
                    enc.method = EncryptionMethod.RC4_128
                    enc.algorithm = "RC4"
                elif version == 4 and revision == 4:
                    cf = re.search(r"/CF\s*<<.*?/StdCF.*?/CFM\s+/(\w+)", enc_obj, re.DOTALL)
                    method_name = cf.group(1) if cf else "AESV2"
                    enc.method = EncryptionMethod.AES_128 if method_name in ("AESV2", "AES") else EncryptionMethod.RC4_128
                    enc.algorithm = method_name
                elif version == 5 and revision in (5, 6, 8):
                    enc.method = EncryptionMethod.AES_256
                    enc.algorithm = "AES-256"
                else:
                    enc.method = EncryptionMethod.UNKNOWN
                break
        except Exception:
            enc.method = EncryptionMethod.UNKNOWN

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _parse_metadata(self, fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        meta = doc.metadata
        try:
            raw = fitz_doc.metadata
            meta.title = raw.get("title", "") or ""
            meta.author = raw.get("author", "") or ""
            meta.subject = raw.get("subject", "") or ""
            meta.keywords = raw.get("keywords", "") or ""
            meta.creator = raw.get("creator", "") or ""
            meta.producer = raw.get("producer", "") or ""
            meta.creation_date = raw.get("creationDate", "") or ""
            meta.modification_date = raw.get("modDate", "") or ""
        except Exception:
            pass

        # XMP metadata stream
        try:
            xref_len = fitz_doc.xref_length()
            for xref in range(1, xref_len):
                try:
                    keys = fitz_doc.xref_get_keys(xref)
                    if "Metadata" in keys:
                        raw_stream = fitz_doc.xref_stream_raw(xref)
                        if raw_stream:
                            meta.xmp_metadata = raw_stream.decode(
                                "utf-8", errors="replace"
                            )
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # Trapped
        try:
            info_xrefs = fitz_doc.xref_get_metadict(-1)
            if isinstance(info_xrefs, dict):
                trapped = info_xrefs.get("Trapped", "")
                if isinstance(trapped, str):
                    meta.trapped = trapped.lstrip("/")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Fonts
    # ------------------------------------------------------------------

    def _parse_fonts(self, fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        handler = FontHandler(fitz_doc)
        doc.fonts = handler.parse_all_fonts()

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def _parse_pages(self, fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        font_handler = FontHandler(fitz_doc)
        global_fonts = doc.fonts

        for page_idx in range(fitz_doc.page_count):
            fitz_page = fitz_doc[page_idx]
            pdf_page = self._parse_single_page(fitz_page, page_idx, font_handler, global_fonts)
            doc.pages.append(pdf_page)
            doc.annotations.extend(pdf_page.annotations)
            doc.form_fields.extend(pdf_page.form_fields)

    def _parse_single_page(
        self,
        fitz_page: fitz.Page,
        page_idx: int,
        font_handler: FontHandler,
        global_fonts: Dict[str, PDFFont],
    ) -> PDFPage:
        page = PDFPage(index=page_idx, page_number=page_idx + 1)
        page.raw_xref = fitz_page.xref

        # -- Boxes --
        page.boxes = self._parse_boxes(fitz_page)
        page.width = fitz_page.rect.width
        page.height = fitz_page.rect.height
        try:
            page.rotation = fitz_page.rotation
        except Exception:
            pass

        # -- Resources --
        page.resources = self._parse_page_resources(fitz_page, font_handler, global_fonts)

        # -- Content blocks from text/image extraction --
        page.content_blocks = self._extract_content_blocks(fitz_page, page)

        # -- Full-text extraction --
        try:
            page.text = fitz_page.get_text("text")
        except Exception:
            page.text = ""

        # -- Annotations --
        page.annotations = self._parse_page_annotations(fitz_page, page_idx)

        # -- Form widgets --
        page.form_fields = self._parse_page_widgets(fitz_page, page_idx)

        return page

    # ------------------------------------------------------------------
    # Page boxes
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_boxes(fitz_page: fitz.Page) -> PageBoxes:
        boxes = PageBoxes()
        try:
            r = fitz_page.rect
            boxes.media_box = (r.x0, r.y0, r.x1, r.y1)
        except Exception:
            pass

        for name, attr in [
            ("crop_box", "CropBox"),
            ("bleed_box", "BleedBox"),
            ("trim_box", "TrimBox"),
            ("art_box", "ArtBox"),
        ]:
            try:
                method = getattr(fitz_page, f"bound", None)
                # Try direct box access
                r = fitz_page.cropbox if name == "crop_box" else None
                if r is None:
                    # Use the rect attribute names
                    if hasattr(fitz_page, name.replace("_box", "rect")):
                        r = getattr(fitz_page, name.replace("_box", "rect"))
                if r is not None:
                    setattr(boxes, name, (r.x0, r.y0, r.x1, r.y1))
            except Exception:
                pass

        # Fallback – read from xref
        try:
            obj = fitz_page._doc.xref_object(fitz_page.xref, compressed=False)
            for box_name, attr in [
                ("/CropBox", "crop_box"),
                ("/BleedBox", "bleed_box"),
                ("/TrimBox", "trim_box"),
                ("/ArtBox", "art_box"),
            ]:
                m = re.search(
                    re.escape(box_name) + r"\s*\[([^\]]+)\]", obj
                )
                if m:
                    vals = m.group(1).split()
                    if len(vals) == 4:
                        try:
                            nums = [float(v) for v in vals]
                            setattr(boxes, attr, tuple(nums))
                        except ValueError:
                            pass
        except Exception:
            pass

        return boxes

    # ------------------------------------------------------------------
    # Page resources
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_page_resources(
        fitz_page: fitz.Page,
        font_handler: FontHandler,
        global_fonts: Dict[str, PDFFont],
    ) -> PDFResource:
        resource = PDFResource()
        try:
            xref_len = fitz_page._doc.xref_length()
            obj = fitz_page._doc.xref_object(fitz_page.xref, compressed=False)
        except Exception:
            return resource

        # Parse fonts referenced on this page
        font_refs = re.findall(r"/Font\s*<<([^>]*)>>", obj, re.DOTALL)
        for block in font_refs:
            for m in re.finditer(
                r"/(\w+)\s+(\d+)\s+\d+\s+R", block
            ):
                fname = m.group(1)
                fxref = int(m.group(2))
                if fname in global_fonts:
                    resource.fonts[fname] = global_fonts[fname]
                else:
                    try:
                        font = font_handler.parse_font(fxref)
                        resource.fonts[fname] = font
                    except Exception:
                        pass

        # Parse ExtGState
        gs_blocks = re.findall(r"/ExtGState\s*<<([^>]*)>>", obj, re.DOTALL)
        for block in gs_blocks:
            for m in re.finditer(r"/(\w+)\s*<<([^>]*)>>", block, re.DOTALL):
                gs_name = m.group(1)
                gs_body = m.group(2)
                gs = ExtGState(name=gs_name)
                op_m = re.search(r"/ca\s+([\d.]+)", gs_body)
                if op_m:
                    gs.opacity = float(op_m.group(1))
                op_m = re.search(r"/CA\s+([\d.]+)", gs_body)
                if op_m:
                    gs.stroke_opacity = float(op_m.group(1))
                bm_m = re.search(r"/BM\s+/(\w+)", gs_body)
                if bm_m:
                    gs.blend_mode = bm_m.group(1)
                lw_m = re.search(r"/LW\s+([\d.]+)", gs_body)
                if lw_m:
                    gs.line_width = float(lw_m.group(1))
                resource.ext_gstates[gs_name] = gs

        # Parse colour spaces
        cs_blocks = re.findall(r"/ColorSpace\s*<<([^>]*)>>", obj, re.DOTALL)
        for block in cs_blocks:
            for m in re.finditer(r"/(\w+)\s+(\w+)", block):
                cs_name = m.group(1)
                cs_type = m.group(2)
                resource.color_spaces[cs_name] = PDFColorSpace(
                    name=cs_name, cs_type=cs_type
                )

        return resource

    # ------------------------------------------------------------------
    # Content blocks extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_content_blocks(
        fitz_page: fitz.Page, pdf_page: PDFPage
    ) -> List[ContentBlock]:
        """Use PyMuPDF's high-level extraction plus low-level access to build blocks."""
        blocks: List[ContentBlock] = []

        # -- Text blocks --
        try:
            text_dict = fitz_page.get_text("dict")
            for block in text_dict.get("blocks", []):
                btype = block.get("type", 0)
                bbox = tuple(block.get("bbox", (0, 0, 0, 0)))

                if btype == 0:  # text
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            tb = TextBlock(
                                text=span.get("text", ""),
                                font_name=span.get("font", ""),
                                font_size=span.get("size", 0),
                                color=_hex_to_rgb(span.get("color", 0)),
                                origin=(span["bbox"][0], span["bbox"][1])
                                if "bbox" in span
                                else (0, 0),
                                bbox=tuple(span.get("bbox", bbox)),
                                flags=span.get("flags", 0),
                            )
                            blocks.append(
                                ContentBlock(
                                    block_type=ObjectType.TEXT,
                                    text_block=tb,
                                    bbox=tb.bbox,
                                )
                            )

                elif btype == 1:  # image
                    image_data = b""
                    try:
                        images = fitz_page.get_images(full=True)
                        if images:
                            img_index = block.get("image", 0)
                            if isinstance(img_index, int) and img_index < len(images):
                                xref = images[img_index][0]
                                image_data = fitz_page._doc.extract_image(xref).get("image", b"")
                    except Exception:
                        pass

                    ib = ImageBlock(
                        image_data=image_data,
                        width=int(block.get("width", 0)),
                        height=int(block.get("height", 0)),
                        bbox=bbox,
                    )
                    blocks.append(
                        ContentBlock(
                            block_type=ObjectType.IMAGE,
                            image_block=ib,
                            bbox=bbox,
                        )
                    )
        except Exception:
            pass

        return blocks

    # ------------------------------------------------------------------
    # Page annotations
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_page_annotations(
        fitz_page: fitz.Page, page_idx: int
    ) -> List[PDFAnnotation]:
        annots: List[PDFAnnotation] = []
        try:
            for annot in fitz_page.annots():
                pa = PDFAnnotation()
                pa.page = page_idx

                # Type
                raw_type = annot.type
                if isinstance(raw_type, (list, tuple)):
                    raw_type = raw_type[1] if len(raw_type) > 1 else str(raw_type[0])
                pa.annot_type = _ANNOT_MAP.get(str(raw_type), AnnotationType.UNKNOWN)

                # Rect
                try:
                    r = annot.rect
                    pa.rect = (r.x0, r.y0, r.x1, r.y1)
                except Exception:
                    pass

                # Text / title / subject
                try:
                    pa.content = annot.info.get("content", "") or ""
                    pa.title = annot.info.get("title", "") or ""
                    pa.subject = annot.info.get("subject", "") or ""
                except Exception:
                    pass

                # Colour
                try:
                    c = annot.colors
                    if "stroke" in c:
                        pa.color = tuple(c["stroke"][:3]) if c["stroke"] else (0, 0, 0)
                    elif "fill" in c:
                        pa.color = tuple(c["fill"][:3]) if c["fill"] else (0, 0, 0)
                except Exception:
                    pass

                # Opacity
                try:
                    pa.opacity = annot.opacity if annot.opacity else 1.0
                except Exception:
                    pass

                # Flags
                try:
                    pa.flags = annot.flags
                except Exception:
                    pass

                # Appearance state
                try:
                    state = annot.appearance_state
                    if state:
                        pa.appearance_state = state
                except Exception:
                    pass

                # Destination / link info
                try:
                    info = annot.info
                    if annot.type and (annot.type[1] == "Link" if isinstance(annot.type, (list, tuple)) else str(annot.type) == "Link"):
                        link = annot.get_dest()
                        if link:
                            if hasattr(link, "page"):
                                pa.destination = {"page": link.page}
                            else:
                                pa.destination = {"dest": str(link)}
                        # URI
                        uri = annot.get_uri()
                        if uri:
                            if pa.destination is None:
                                pa.destination = {}
                            pa.destination["uri"] = uri
                except Exception:
                    pass

                # Quad points for highlight / strikeout etc
                try:
                    qp = annot.get_quad_points()
                    if qp:
                        pa.quad_points = [
                            (qp[i], qp[i + 1], qp[i + 2], qp[i + 3])
                            for i in range(0, len(qp), 4)
                        ]
                except Exception:
                    pass

                # Border
                try:
                    border = annot.border
                    if border and (border.get("width", 0) or border.get("dashes", [])):
                        pa.border = border
                except Exception:
                    pass

                # File attachment info
                if pa.annot_type == AnnotationType.FILE_ATTACHMENT:
                    try:
                        fs = annot.file_info
                        if fs:
                            pa.file_spec = fs
                    except Exception:
                        pass

                annots.append(pa)
        except Exception:
            pass

        return annots

    # ------------------------------------------------------------------
    # Form widgets
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_page_widgets(
        fitz_page: fitz.Page, page_idx: int
    ) -> List[PDFFormField]:
        fields: List[PDFFormField] = []
        try:
            for widget in fitz_page.widgets():
                ff = PDFFormField()
                ff.page = page_idx

                # Field type
                wtype = widget.field_type_string if hasattr(widget, "field_type_string") else ""
                ff.field_type = _FORM_TYPE_MAP.get(wtype, FormFieldType.UNKNOWN)

                # Field flags
                ff.flags = widget.field_flags if hasattr(widget, "field_flags") else 0

                # Name
                ff.name = widget.field_name if hasattr(widget, "field_name") else ""

                # Value
                ff.value = widget.field_value if hasattr(widget, "field_value") else ""

                # Rect
                try:
                    r = widget.rect
                    ff.rect = (r.x0, r.y0, r.x1, r.y1)
                except Exception:
                    pass

                # Font
                ff.font_name = widget.text_font if hasattr(widget, "text_font") else ""
                ff.font_size = widget.text_fontsize if hasattr(widget, "text_fontsize") else 0

                # Max length
                ff.max_length = widget.maxlen if hasattr(widget, "maxlen") else 0

                # Choice values (combo / list)
                if hasattr(widget, "choice_values") and widget.choice_values:
                    ff.options = [
                        {"value": v, "label": v} for v in widget.choice_values
                    ]

                # Tooltip
                ff.tooltip = widget.tooltip if hasattr(widget, "tooltip") else ""

                # On / off values for checkboxes / radios
                ff.on_value = widget.button_states()[0].get("on", "Yes") if hasattr(widget, "button_states") and widget.button_states() else "Yes"

                # Locked
                ff.locked = bool(ff.flags & (1 << 8))

                # Required
                ff.required = bool(ff.flags & (1 << 1))

                fields.append(ff)
        except Exception:
            pass

        return fields

    # ------------------------------------------------------------------
    # Bookmarks / outlines
    # ------------------------------------------------------------------

    def _parse_bookmarks(self, fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        try:
            toc = fitz_doc.get_toc(simple=False)
        except Exception:
            return

        for item in toc:
            level, title, page_or_dest = item[0], item[1], item[2] if len(item) > 1 else -1
            bm = PDFBookmark(
                title=title,
                level=level,
                page=page_or_dest if isinstance(page_or_dest, int) else -1,
            )
            # Additional destination info
            if isinstance(item, (list, tuple)) and len(item) > 2:
                dest_info = item[2]
                if isinstance(dest_info, dict):
                    bm.dest = dest_info
                elif isinstance(dest_info, list):
                    bm.dest = {"dest": dest_info}

            doc.bookmarks.append(bm)

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_attachments(fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        try:
            for name in fitz_doc.annexes():
                att = PDFAttachment(name=name)
                try:
                    info = fitz_doc.annex_info(name)
                    att.description = info.get("description", "")
                    att.mime_type = info.get("file", "").rsplit(".", 1)[-1] if info.get("file") else ""
                    att.creation_date = info.get("creationDate", "")
                    att.modification_date = info.get("modDate", "")
                except Exception:
                    pass

                try:
                    att.data = fitz_doc.extract_att(name)
                except Exception:
                    att.data = b""

                doc.attachments.append(att)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Form fields (all pages)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_form_fields(fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        # Collect unique fields across all pages
        seen = set()
        for page in doc.pages:
            for ff in page.form_fields:
                if ff.name and ff.name not in seen:
                    doc.form_fields.append(ff)
                    seen.add(ff.name)

        # Also try low-level form traversal
        try:
            xref_len = fitz_doc.xref_length()
            for xref in range(1, xref_len):
                try:
                    obj_type = fitz_doc.xref_get_key(xref, "Type")
                    if obj_type[1] != "/Annot":
                        continue
                    subtype = fitz_doc.xref_get_key(xref, "Subtype")
                    if subtype[1] != "/Widget":
                        continue
                    # Skip if already collected
                except Exception:
                    continue
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Digital signatures
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_signatures(fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        try:
            sig_fields = fitz_doc.get_sigflags()
        except Exception:
            sig_fields = 0

        if not sig_fields:
            return

        # Walk annotations looking for signature widgets
        try:
            for page_idx in range(fitz_doc.page_count):
                fitz_page = fitz_doc[page_idx]
                for widget in fitz_page.widgets():
                    if not hasattr(widget, "field_type_string"):
                        continue
                    if widget.field_type_string != "Signature":
                        continue

                    sig = PDFSignature()
                    sig.name = widget.field_name if hasattr(widget, "field_name") else ""
                    sig.page = page_idx

                    try:
                        r = widget.rect
                        sig.rect = (r.x0, r.y0, r.x1, r.y1)
                    except Exception:
                        pass

                    # Extract from the field dict
                    try:
                        field_obj = fitz_doc.xref_object(widget.xref, compressed=False)
                        m = re.search(r"/Reason\s*\(([^)]*)\)", field_obj)
                        if m:
                            sig.reason = m.group(1)
                        m = re.search(r"/Location\s*\(([^)]*)\)", field_obj)
                        if m:
                            sig.location = m.group(1)
                        m = re.search(r"/M\s*\(([^)]*)\)", field_obj)
                        if m:
                            sig.date = m.group(1)
                        m = re.search(r"/ContactInfo\s*\(([^)]*)\)", field_obj)
                        if m:
                            sig.contact_info = m.group(1)
                        sf = re.search(r"/SubFilter\s+/(\w+)", field_obj)
                        if sf:
                            sig.sub_filter = sf.group(1)
                    except Exception:
                        pass

                    doc.signatures.append(sig)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Global annotations
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_global_annotations(fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        """Collect annotations that are not directly on a page (AcroForm etc)."""
        # Already collected per-page in _parse_pages
        pass

    # ------------------------------------------------------------------
    # Output intents
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_output_intents(fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        try:
            xref_len = fitz_doc.xref_length()
            for xref in range(1, xref_len):
                try:
                    obj = fitz_doc.xref_object(xref, compressed=False)
                except Exception:
                    continue
                if "/OutputIntents" not in obj:
                    continue

                intent_matches = re.finditer(
                    r"<<\s*(.*?)\s*>>", obj[obj.index("/OutputIntents") :], re.DOTALL
                )
                for im in intent_matches:
                    body = im.group(1)
                    oi = PDFOutputIntent()
                    st = re.search(r"/Subtype\s+/(\w+)", body)
                    if st:
                        oi.subtype = st.group(1)
                    oc = re.search(r"/OutputCondition\s*\(([^)]*)\)", body)
                    if oc:
                        oi.output_condition = oc.group(1)
                    oci = re.search(r"/OutputConditionIdentifier\s*\(([^)]*)\)", body)
                    if oci:
                        oi.output_condition_id = oci.group(1)
                    rn = re.search(r"/RegistryName\s*\(([^)]*)\)", body)
                    if rn:
                        oi.registry_name = rn.group(1)
                    inf = re.search(r"/Info\s*\(([^)]*)\)", body)
                    if inf:
                        oi.info = inf.group(1)
                    doc.output_intents.append(oi)
                break  # Only one /OutputIntents array per doc
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Threads / article beads
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_threads(fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        try:
            xref_len = fitz_doc.xref_length()
            thread_xrefs: set = set()
            for xref in range(1, xref_len):
                try:
                    obj = fitz_doc.xref_object(xref, compressed=False)
                except Exception:
                    continue
                if "/Thread" not in obj and "/Bead" not in obj:
                    continue

                # Detect thread dictionaries
                if "/Type" in obj and "/Thread" in obj:
                    thread = PDFThread()
                    ti = re.search(r"/Info\s*\(([^)]*)\)", obj)
                    if ti:
                        thread.info = ti.group(1)
                    thread_xrefs.add(xref)
                    doc.threads.append(thread)

            # Collect beads
            for xref in range(1, xref_len):
                try:
                    obj = fitz_doc.xref_object(xref, compressed=False)
                except Exception:
                    continue
                if "/Bead" not in obj or "/Rect" not in obj:
                    continue

                bead = PDFThreadBead()
                rect_m = re.search(r"/Rect\s*\[([^\]]+)\]", obj)
                if rect_m:
                    vals = rect_m.group(1).split()
                    if len(vals) == 4:
                        try:
                            bead.rect = tuple(float(v) for v in vals)
                        except ValueError:
                            pass

                page_m = re.search(r"/P\s+(\d+)\s+\d+\s+R", obj)
                if page_m:
                    try:
                        page_xref = int(page_m.group(1))
                        # Find page index
                        for pi in range(fitz_doc.page_count):
                            if fitz_doc[pi].xref == page_xref:
                                bead.page = pi
                                break
                    except Exception:
                        pass

                if doc.threads:
                    doc.threads[-1].beads.append(bead)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Structure tree (PDF/UA)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_structure_tree(fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        try:
            xref_len = fitz_doc.xref_length()
            for xref in range(1, xref_len):
                try:
                    obj = fitz_doc.xref_object(xref, compressed=False)
                except Exception:
                    continue
                if "/StructTreeRoot" not in obj:
                    continue

                root_ref = re.search(r"/StructTreeRoot\s+(\d+)\s+\d+\s+R", obj)
                if not root_ref:
                    continue

                root_xref = int(root_ref.group(1))
                doc.structure_tree = _parse_struct_node(fitz_doc, root_xref)
                break
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Mark info
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_mark_info(fitz_doc: fitz.Document, doc: PDFDocument) -> None:
        try:
            xref_len = fitz_doc.xref_length()
            for xref in range(1, xref_len):
                try:
                    obj = fitz_doc.xref_object(xref, compressed=False)
                except Exception:
                    continue
                if "/MarkInfo" not in obj:
                    continue

                mi = PDFMarkInfo()
                if "/Marked" in obj:
                    mi.marked = "/true" in obj.lower() or "/Marked /true" in obj
                if "/Suspects" in obj:
                    mi.Suspects = "/Suspects /true" in obj
                if "/UserProperties" in obj:
                    mi.user_properties = "/UserProperties /true" in obj
                doc.mark_info = mi
                break
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(color: int) -> Tuple[float, float, float]:
    """Convert an integer colour (from fitz) to (r, g, b) floats."""
    if isinstance(color, int):
        r = ((color >> 16) & 0xFF) / 255.0
        g = ((color >> 8) & 0xFF) / 255.0
        b = (color & 0xFF) / 255.0
        return (r, g, b)
    return (0.0, 0.0, 0.0)


def _parse_struct_node(
    fitz_doc: fitz.Document, xref: int
) -> Optional[PDFStructureElement]:
    """Recursively parse a structure-tree node."""
    try:
        obj = fitz_doc.xref_object(xref, compressed=False)
    except Exception:
        return None

    node = PDFStructureElement()

    # Tag
    tag_m = re.search(r"/S\s+/(\w+)", obj)
    if tag_m:
        node.tag = tag_m.group(1)

    # Alt text
    alt_m = re.search(r"/Alt\s*\(([^)]*)\)", obj)
    if alt_m:
        node.alt = alt_m.group(1)
    alt_m2 = re.search(r"/Alt\s*<([^>]*)>", obj)
    if alt_m2:
        try:
            node.alt = bytes.fromhex(alt_m2.group(1)).decode("utf-16-be", errors="replace")
        except Exception:
            node.alt = alt_m2.group(1)

    # Actual text
    at_m = re.search(r"/ActualText\s*\(([^)]*)\)", obj)
    if at_m:
        node.actual_text = at_m.group(1)

    # Language
    lang_m = re.search(r"/Lang\s*\(([^)]*)\)", obj)
    if lang_m:
        node.language = lang_m.group(1)

    # Title
    title_m = re.search(r"/T\s*\(([^)]*)\)", obj)
    if title_m:
        node.title = title_m.group(1)

    # Content references
    for m in re.finditer(r"(\d+)\s+\d+\s+R", obj):
        ref = int(m.group(1))
        # Heuristic: if it's not a child ref, it's content
        node.content_refs.append(ref)

    # Children
    kids_m = re.search(r"/K\s*\[([^\]]+)\]", obj)
    if kids_m:
        raw = kids_m.group(1)
        for child_ref_m in re.finditer(r"(\d+)\s+\d+\s+R", raw):
            child_xref = int(child_ref_m.group(1))
            child = _parse_struct_node(fitz_doc, child_xref)
            if child:
                child.parent = node
                node.children.append(child)

    return node


_FORM_TYPE_MAP: Dict[str, FormFieldType] = {
    "Button": FormFieldType.BUTTON,
    "CheckBox": FormFieldType.CHECKBOX,
    "RadioButton": FormFieldType.RADIO,
    "ComboBox": FormFieldType.COMBO,
    "ListBox": FormFieldType.LIST,
    "Text": FormFieldType.TEXT,
    "Signature": FormFieldType.SIGNATURE,
}
