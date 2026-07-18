"""PDF object model classes for the engine intermediate representation.

All parser modules produce instances of these classes.  Every class exposes
``__init__``, ``__repr__``, and ``to_dict()`` for easy serialisation and
debugging.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ObjectType(Enum):
    """Discriminator for content blocks."""
    TEXT = "text"
    IMAGE = "image"
    PATH = "path"


class AnnotationType(Enum):
    """Standard PDF annotation types (PDF 2.0 Table 179)."""
    TEXT = "Text"
    LINK = "Link"
    FREE_TEXT = "FreeText"
    LINE = "Line"
    SQUARE = "Square"
    CIRCLE = "Circle"
    POLYGON = "Polygon"
    POLY_LINE = "PolyLine"
    HIGHLIGHT = "Highlight"
    UNDERLINE = "Underline"
    SQUIGGLY = "Squiggly"
    STRIKEOUT = "StrikeOut"
    STAMP = "Stamp"
    CARET = "Caret"
    INK = "Ink"
    POPUP = "Popup"
    FILE_ATTACHMENT = "FileAttachment"
    SOUND = "Sound"
    MOVIE = "Movie"
    WIDGET = "Widget"
    SCREEN = "Screen"
    MARKUP = "Markup"
    D_3D = "3D"
    REDACT = "Redact"
    REDACT2 = "Redact"
    PROJECTION = "Projection"
    RICH_MEDIA = "RichMedia"
    UNKNOWN = "Unknown"


class FormFieldType(Enum):
    """PDF form field types."""
    NONE = "None"
    BUTTON = "Button"
    CHECKBOX = "Checkbox"
    RADIO = "Radio"
    COMBO = "ComboBox"
    LIST = "ListBox"
    TEXT = "Text"
    SIGNATURE = "Signature"
    UNKNOWN = "Unknown"


class FontType(Enum):
    """PDF font subtypes."""
    TYPE0 = "Type0"
    TYPE1 = "Type1"
    TYPE3 = "Type3"
    TRUETYPE = "TrueType"
    CID_FONT = "CIDFont"
    UNKNOWN = "Unknown"


class EncryptionMethod(Enum):
    """Encryption methods."""
    NONE = "None"
    RC4_40 = "RC4-40"
    RC4_128 = "RC4-128"
    AES_128 = "AES-128"
    AES_256 = "AES-256"
    AES_256_R5 = "AES-256-R5"
    UNKNOWN = "Unknown"


# ---------------------------------------------------------------------------
# Content blocks
# ---------------------------------------------------------------------------

@dataclass
class TextBlock:
    """A span of text extracted from a content stream."""
    text: str = ""
    font_name: str = ""
    font_size: float = 0.0
    color: Tuple[float, ...] = (0.0, 0.0, 0.0)
    origin: Tuple[float, float] = (0.0, 0.0)
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    flags: int = 0  # bit 0=superscript, 1=italic, 2=subscript
    char_spacing: float = 0.0
    word_spacing: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "color": list(self.color),
            "origin": list(self.origin),
            "bbox": list(self.bbox),
            "flags": self.flags,
            "char_spacing": self.char_spacing,
            "word_spacing": self.word_spacing,
        }

    def __repr__(self) -> str:
        preview = self.text[:40] + ("..." if len(self.text) > 40 else "")
        return (
            f"TextBlock(font={self.font_name!r}, size={self.font_size:.1f}, "
            f"text={preview!r}, bbox={self.bbox})"
        )


@dataclass
class ImageBlock:
    """An image drawn via the ``Do`` operator."""
    image_data: bytes = b""
    width: int = 0
    height: int = 0
    bpc: int = 8
    color_space: str = ""
    filter_name: str = ""
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    transform: Tuple[float, float, float, float, float, float] = (1, 0, 0, 1, 0, 0)
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "bpc": self.bpc,
            "color_space": self.color_space,
            "filter_name": self.filter_name,
            "bbox": list(self.bbox),
            "transform": list(self.transform),
            "name": self.name,
            "image_size_bytes": len(self.image_data),
        }

    def __repr__(self) -> str:
        return (
            f"ImageBlock(name={self.name!r}, {self.width}x{self.height}, "
            f"bbox={self.bbox})"
        )


@dataclass
class PathSegment:
    """A single path segment (move / line / curve)."""
    operator: str = ""
    points: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class PathBlock:
    """A vector path drawn in a content stream."""
    segments: List[PathSegment] = field(default_factory=list)
    stroke_color: Tuple[float, ...] = (0.0, 0.0, 0.0)
    fill_color: Optional[Tuple[float, ...]] = None
    line_width: float = 1.0
    close_path: bool = False
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segments": [
                {"operator": s.operator, "points": [list(p) for p in s.points]}
                for s in self.segments
            ],
            "stroke_color": list(self.stroke_color),
            "fill_color": list(self.fill_color) if self.fill_color is not None else None,
            "line_width": self.line_width,
            "close_path": self.close_path,
            "bbox": list(self.bbox),
        }

    def __repr__(self) -> str:
        return (
            f"PathBlock(segments={len(self.segments)}, "
            f"bbox={self.bbox})"
        )


@dataclass
class ContentBlock:
    """Wrapper that unifies text, image, and path blocks."""
    block_type: ObjectType = ObjectType.TEXT
    text_block: Optional[TextBlock] = None
    image_block: Optional[ImageBlock] = None
    path_block: Optional[PathBlock] = None
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "block_type": self.block_type.value,
            "bbox": list(self.bbox),
        }
        if self.text_block is not None:
            d["text"] = self.text_block.to_dict()
        if self.image_block is not None:
            d["image"] = self.image_block.to_dict()
        if self.path_block is not None:
            d["path"] = self.path_block.to_dict()
        return d

    def __repr__(self) -> str:
        inner = self.text_block or self.image_block or self.path_block
        return f"ContentBlock(type={self.block_type.value}, inner={inner!r})"


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------

@dataclass
class PDFAnnotation:
    """Represents a single PDF annotation."""
    annot_type: AnnotationType = AnnotationType.UNKNOWN
    rect: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    content: str = ""
    title: str = ""
    subject: str = ""
    color: Tuple[float, float, float] = (1.0, 1.0, 0.0)
    opacity: float = 1.0
    flags: int = 0
    appearance_state: str = ""
    page: int = -1
    open: bool = False
    destination: Optional[Dict[str, Any]] = None
    file_spec: Optional[Dict[str, Any]] = None
    quad_points: Optional[List[Tuple[float, ...]]] = None
    border: Optional[Dict[str, Any]] = None
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "type": self.annot_type.value,
            "rect": list(self.rect),
            "content": self.content,
            "title": self.title,
            "subject": self.subject,
            "color": list(self.color),
            "opacity": self.opacity,
            "flags": self.flags,
            "page": self.page,
        }
        if self.appearance_state:
            d["appearance_state"] = self.appearance_state
        if self.open:
            d["open"] = True
        if self.destination is not None:
            d["destination"] = self.destination
        if self.file_spec is not None:
            d["file_spec"] = self.file_spec
        if self.quad_points is not None:
            d["quad_points"] = [list(q) for q in self.quad_points]
        if self.border is not None:
            d["border"] = self.border
        if self.custom:
            d["custom"] = self.custom
        return d

    def __repr__(self) -> str:
        preview = self.content[:30] + ("..." if len(self.content) > 30 else "")
        return (
            f"PDFAnnotation(type={self.annot_type.value}, "
            f"rect={self.rect}, content={preview!r})"
        )


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

@dataclass
class PDFFont:
    """Information about a font resource."""
    name: str = ""
    base_font: str = ""
    font_type: FontType = FontType.UNKNOWN
    encoding: str = ""
    embedded: bool = False
    subset: bool = False
    differences: List[Tuple[int, str]] = field(default_factory=list)
    ToUnicode: Optional[str] = None
    first_char: int = 0
    last_char: int = 0
    widths: List[float] = field(default_factory=list)
    descent: float = 0.0
    ascent: float = 0.0
    cap_height: float = 0.0
    italic_angle: float = 0.0
    descriptor_flags: int = 0
    family: str = ""
    ref: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "base_font": self.base_font,
            "type": self.font_type.value,
            "encoding": self.encoding,
            "embedded": self.embedded,
            "subset": self.subset,
            "ascent": self.ascent,
            "descent": self.descent,
            "cap_height": self.cap_height,
            "italic_angle": self.italic_angle,
        }
        if self.differences:
            d["differences"] = [[code, name] for code, name in self.differences]
        if self.ToUnicode is not None:
            d["to_unicode_present"] = True
        if self.family:
            d["family"] = self.family
        if self.ref is not None:
            d["ref"] = self.ref
        return d

    def __repr__(self) -> str:
        return (
            f"PDFFont(name={self.name!r}, base={self.base_font!r}, "
            f"type={self.font_type.value}, embedded={self.embedded})"
        )


# ---------------------------------------------------------------------------
# Form fields
# ---------------------------------------------------------------------------

@dataclass
class PDFFormField:
    """A single interactive form field."""
    field_type: FormFieldType = FormFieldType.UNKNOWN
    name: str = ""
    alt_name: str = ""
    value: Any = None
    default_value: Any = None
    rect: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    options: List[Dict[str, Any]] = field(default_factory=list)
    flags: int = 0
    max_length: int = 0
    justification: int = 0
    font_name: str = ""
    font_size: float = 0.0
    page: int = -1
    children: List[str] = field(default_factory=list)
    on_value: str = "Yes"
    off_value: str = "Off"
    tooltip: str = ""
    locked: bool = False
    required: bool = False
    no_export: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "field_type": self.field_type.value,
            "name": self.name,
            "alt_name": self.alt_name,
            "value": self.value,
            "default_value": self.default_value,
            "rect": list(self.rect),
            "flags": self.flags,
            "max_length": self.max_length,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "page": self.page,
            "tooltip": self.tooltip,
            "locked": self.locked,
            "required": self.required,
            "no_export": self.no_export,
        }
        if self.options:
            d["options"] = self.options
        if self.children:
            d["children"] = self.children
        return d

    def __repr__(self) -> str:
        return (
            f"PDFFormField(type={self.field_type.value}, "
            f"name={self.name!r}, value={self.value!r})"
        )


# ---------------------------------------------------------------------------
# Bookmarks / Outlines
# ---------------------------------------------------------------------------

@dataclass
class PDFBookmark:
    """A bookmark (outline) entry."""
    title: str = ""
    level: int = 0
    page: int = -1
    page_ref: Optional[int] = None
    dest: Optional[Dict[str, Any]] = None
    color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    closed: bool = False
    children: List["PDFBookmark"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "title": self.title,
            "level": self.level,
            "page": self.page,
            "color": list(self.color),
            "closed": self.closed,
        }
        if self.dest is not None:
            d["dest"] = self.dest
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    def __repr__(self) -> str:
        return (
            f"PDFBookmark(title={self.title!r}, level={self.level}, "
            f"page={self.page})"
        )


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

@dataclass
class PDFAttachment:
    """An embedded file / attachment."""
    name: str = ""
    description: str = ""
    mime_type: str = ""
    data: bytes = b""
    creation_date: str = ""
    modification_date: str = ""
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "mime_type": self.mime_type,
            "size_bytes": len(self.data),
            "creation_date": self.creation_date,
            "modification_date": self.modification_date,
        }

    def __repr__(self) -> str:
        return (
            f"PDFAttachment(name={self.name!r}, mime={self.mime_type!r}, "
            f"size={len(self.data)})"
        )


# ---------------------------------------------------------------------------
# Digital signatures
# ---------------------------------------------------------------------------

@dataclass
class PDFSignature:
    """A digital signature field."""
    name: str = ""
    reason: str = ""
    location: str = ""
    contact_info: str = ""
    date: str = ""
    signer_name: str = ""
    cert: Optional[bytes] = None
    byte_range: Optional[Tuple[int, int, int]] = None
    contents: Optional[bytes] = None
    sub_filter: str = ""
    filter_name: str = ""
    rect: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    page: int = -1
    locked: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "reason": self.reason,
            "location": self.location,
            "contact_info": self.contact_info,
            "date": self.date,
            "signer_name": self.signer_name,
            "sub_filter": self.sub_filter,
            "filter": self.filter_name,
            "rect": list(self.rect),
            "page": self.page,
            "has_cert": self.cert is not None,
        }

    def __repr__(self) -> str:
        return (
            f"PDFSignature(name={self.name!r}, signer={self.signer_name!r}, "
            f"date={self.date!r})"
        )


# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------

@dataclass
class PDFEncryption:
    """Encryption metadata for the document."""
    method: EncryptionMethod = EncryptionMethod.NONE
    user_password: str = ""
    owner_password: str = ""
    permissions: int = -1
    key_length: int = 0
    algorithm: str = ""
    version: int = 0
    revision: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "key_length": self.key_length,
            "algorithm": self.algorithm,
            "version": self.version,
            "revision": self.revision,
            "permissions": self.permissions,
            "has_user_password": bool(self.user_password),
            "has_owner_password": bool(self.owner_password),
        }

    def __repr__(self) -> str:
        return (
            f"PDFEncryption(method={self.method.value}, "
            f"key_length={self.key_length})"
        )


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@dataclass
class ExtGState:
    """Graphics state override from an ExtGState dictionary."""
    name: str = ""
    opacity: float = 1.0
    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0
    blend_mode: str = ""
    line_width: float = 1.0
    line_cap: int = 0
    line_join: int = 0
    miter_limit: float = 10.0
    dash: Optional[List[float]] = None
    font: str = ""
    font_size: float = 0.0
    render_intent: str = ""
    stroke_adjust: bool = False
    overprint: bool = False
    overprint_mode: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "opacity": self.opacity,
            "fill_opacity": self.fill_opacity,
            "stroke_opacity": self.stroke_opacity,
            "blend_mode": self.blend_mode,
            "line_width": self.line_width,
            "line_cap": self.line_cap,
            "line_join": self.line_join,
            "miter_limit": self.miter_limit,
            "render_intent": self.render_intent,
            "stroke_adjust": self.stroke_adjust,
            "overprint": self.overprint,
            "overprint_mode": self.overprint_mode,
        }
        if self.dash is not None:
            d["dash"] = self.dash
        return d

    def __repr__(self) -> str:
        return f"ExtGState(name={self.name!r}, opacity={self.opacity})"


@dataclass
class PDFColorSpace:
    """A colour space definition."""
    name: str = ""
    cs_type: str = ""
    components: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.cs_type,
            "components": [
                c if not isinstance(c, bytes) else f"<{len(c)} bytes>"
                for c in self.components
            ],
        }

    def __repr__(self) -> str:
        return f"PDFColorSpace(name={self.name!r}, type={self.cs_type!r})"


@dataclass
class PDFPattern:
    """A pattern resource."""
    name: str = ""
    pattern_type: int = 0
    paint: int = 0
    tiled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "pattern_type": self.pattern_type,
            "paint": self.paint,
            "tiled": self.tiled,
        }

    def __repr__(self) -> str:
        return f"PDFPattern(name={self.name!r})"


@dataclass
class PDFResource:
    """Page / document-level resource dictionary."""
    fonts: Dict[str, PDFFont] = field(default_factory=dict)
    color_spaces: Dict[str, PDFColorSpace] = field(default_factory=dict)
    patterns: Dict[str, PDFPattern] = field(default_factory=dict)
    ext_gstates: Dict[str, ExtGState] = field(default_factory=dict)
    images: Dict[str, Any] = field(default_factory=dict)
    x_objects: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fonts": {k: v.to_dict() for k, v in self.fonts.items()},
            "color_spaces": {k: v.to_dict() for k, v in self.color_spaces.items()},
            "patterns": {k: v.to_dict() for k, v in self.patterns.items()},
            "ext_gstates": {k: v.to_dict() for k, v in self.ext_gstates.items()},
            "images": {k: "..." for k in self.images},
            "x_objects": {k: "..." for k in self.x_objects},
        }

    def __repr__(self) -> str:
        return (
            f"PDFResource(fonts={len(self.fonts)}, "
            f"color_spaces={len(self.color_spaces)}, "
            f"ext_gstates={len(self.ext_gstates)})"
        )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@dataclass
class PageBoxes:
    """All standard page boxes."""
    media_box: Tuple[float, float, float, float] = (0.0, 0.0, 612.0, 792.0)
    crop_box: Optional[Tuple[float, float, float, float]] = None
    bleed_box: Optional[Tuple[float, float, float, float]] = None
    trim_box: Optional[Tuple[float, float, float, float]] = None
    art_box: Optional[Tuple[float, float, float, float]] = None

    def effective_box(self) -> Tuple[float, float, float, float]:
        return self.crop_box or self.media_box

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"media_box": list(self.media_box)}
        if self.crop_box is not None:
            d["crop_box"] = list(self.crop_box)
        if self.bleed_box is not None:
            d["bleed_box"] = list(self.bleed_box)
        if self.trim_box is not None:
            d["trim_box"] = list(self.trim_box)
        if self.art_box is not None:
            d["art_box"] = list(self.art_box)
        return d

    def __repr__(self) -> str:
        return f"PageBoxes(media={self.media_box}, crop={self.crop_box})"


@dataclass
class PDFPage:
    """Represents a single page in the document."""
    index: int = 0
    page_number: int = 1
    boxes: PageBoxes = field(default_factory=PageBoxes)
    width: float = 612.0
    height: float = 792.0
    rotation: int = 0
    content_blocks: List[ContentBlock] = field(default_factory=list)
    annotations: List[PDFAnnotation] = field(default_factory=list)
    form_fields: List[PDFFormField] = field(default_factory=list)
    resources: PDFResource = field(default_factory=PDFResource)
    text: str = ""
    raw_xref: int = 0

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        return self.boxes.effective_box()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "boxes": self.boxes.to_dict(),
            "content_block_count": len(self.content_blocks),
            "annotation_count": len(self.annotations),
            "form_field_count": len(self.form_fields),
            "text_length": len(self.text),
            "raw_xref": self.raw_xref,
        }

    def __repr__(self) -> str:
        return (
            f"PDFPage(index={self.index}, {self.width:.0f}x{self.height:.0f}, "
            f"rotation={self.rotation}, blocks={len(self.content_blocks)})"
        )


# ---------------------------------------------------------------------------
# Output intent
# ---------------------------------------------------------------------------

@dataclass
class PDFOutputIntent:
    """An output intent dictionary."""
    subtype: str = ""
    output_condition: str = ""
    output_condition_id: str = ""
    registry_name: str = ""
    info: str = ""
    dest_output_profile: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subtype": self.subtype,
            "output_condition": self.output_condition,
            "output_condition_id": self.output_condition_id,
            "registry_name": self.registry_name,
            "info": self.info,
            "has_profile": self.dest_output_profile is not None,
        }

    def __repr__(self) -> str:
        return f"PDFOutputIntent(subtype={self.subtype!r}, info={self.info!r})"


# ---------------------------------------------------------------------------
# Structure tree (PDF/UA)
# ---------------------------------------------------------------------------

@dataclass
class PDFStructureElement:
    """A node in the structure tree."""
    tag: str = ""
    alt: str = ""
    actual_text: str = ""
    language: str = ""
    title: str = ""
    children: List["PDFStructureElement"] = field(default_factory=list)
    content_refs: List[int] = field(default_factory=list)
    parent: Optional["PDFStructureElement"] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "tag": self.tag,
            "alt": self.alt,
            "actual_text": self.actual_text,
            "language": self.language,
        }
        if self.title:
            d["title"] = self.title
        if self.content_refs:
            d["content_refs"] = self.content_refs
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    def __repr__(self) -> str:
        return (
            f"PDFStructureElement(tag={self.tag!r}, alt={self.alt!r}, "
            f"children={len(self.children)})"
        )


@dataclass
class PDFMarkInfo:
    """Mark information dictionary."""
    marked: bool = False
    user_properties: bool = False
    Suspects: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "marked": self.marked,
            "user_properties": self.user_properties,
            "suspects": self.Suspects,
        }

    def __repr__(self) -> str:
        return f"PDFMarkInfo(marked={self.marked})"


# ---------------------------------------------------------------------------
# Thread / article beads
# ---------------------------------------------------------------------------

@dataclass
class PDFThreadBead:
    """A bead in an article thread."""
    rect: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    page: int = -1
    next_ref: Optional[int] = None
    thread_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rect": list(self.rect),
            "page": self.page,
            "thread_id": self.thread_id,
        }

    def __repr__(self) -> str:
        return f"PDFThreadBead(thread={self.thread_id!r}, page={self.page})"


@dataclass
class PDFThread:
    """An article thread."""
    info: str = ""
    beads: List[PDFThreadBead] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "info": self.info,
            "bead_count": len(self.beads),
            "beads": [b.to_dict() for b in self.beads],
        }

    def __repr__(self) -> str:
        return f"PDFThread(info={self.info!r}, beads={len(self.beads)})"


# ---------------------------------------------------------------------------
# Document metadata wrapper
# ---------------------------------------------------------------------------

@dataclass
class PDFMetadata:
    """Document-level metadata."""
    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: str = ""
    creator: str = ""
    producer: str = ""
    creation_date: str = ""
    modification_date: str = ""
    trapped: str = ""
    xmp_metadata: Optional[str] = None
    custom: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "keywords": self.keywords,
            "creator": self.creator,
            "producer": self.producer,
            "creation_date": self.creation_date,
            "modification_date": self.modification_date,
            "trapped": self.trapped,
            "has_xmp": self.xmp_metadata is not None,
        }
        if self.custom:
            d["custom"] = self.custom
        return d

    def __repr__(self) -> str:
        return (
            f"PDFMetadata(title={self.title!r}, author={self.author!r}, "
            f"creator={self.creator!r})"
        )


# ---------------------------------------------------------------------------
# Top-level document
# ---------------------------------------------------------------------------

@dataclass
class PDFDocument:
    """Top-level representation of a parsed PDF."""
    file_path: str = ""
    metadata: PDFMetadata = field(default_factory=PDFMetadata)
    pages: List[PDFPage] = field(default_factory=list)
    fonts: Dict[str, PDFFont] = field(default_factory=dict)
    resources: PDFResource = field(default_factory=PDFResource)
    bookmarks: List[PDFBookmark] = field(default_factory=list)
    annotations: List[PDFAnnotation] = field(default_factory=list)
    form_fields: List[PDFFormField] = field(default_factory=list)
    attachments: List[PDFAttachment] = field(default_factory=list)
    signatures: List[PDFSignature] = field(default_factory=list)
    encryption: PDFEncryption = field(default_factory=PDFEncryption)
    output_intents: List[PDFOutputIntent] = field(default_factory=list)
    structure_tree: Optional[PDFStructureElement] = None
    mark_info: PDFMarkInfo = field(default_factory=PDFMarkInfo)
    threads: List[PDFThread] = field(default_factory=list)
    page_count: int = 0
    version: str = ""

    def page(self, index: int) -> PDFPage:
        if 0 <= index < len(self.pages):
            return self.pages[index]
        raise IndexError(f"Page index {index} out of range (0-{len(self.pages) - 1})")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "version": self.version,
            "page_count": self.page_count,
            "metadata": self.metadata.to_dict(),
            "encryption": self.encryption.to_dict(),
            "fonts": {k: v.to_dict() for k, v in self.fonts.items()},
            "pages": [p.to_dict() for p in self.pages],
            "bookmarks": [b.to_dict() for b in self.bookmarks],
            "annotations": [a.to_dict() for a in self.annotations],
            "form_fields": [f.to_dict() for f in self.form_fields],
            "attachments": [a.to_dict() for a in self.attachments],
            "signatures": [s.to_dict() for s in self.signatures],
            "output_intents": [o.to_dict() for o in self.output_intents],
            "structure_tree": (
                self.structure_tree.to_dict() if self.structure_tree else None
            ),
            "mark_info": self.mark_info.to_dict(),
            "threads": [t.to_dict() for t in self.threads],
        }

    def __repr__(self) -> str:
        return (
            f"PDFDocument(file={self.file_path!r}, pages={self.page_count}, "
            f"fonts={len(self.fonts)}, version={self.version!r})"
        )
