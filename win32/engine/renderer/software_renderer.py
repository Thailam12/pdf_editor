"""Pure Python PDF renderer backed by PyMuPDF for high-performance page rendering.

Renders PDF pages to PIL Images with full support for text, images, vector paths,
graphics state, color spaces, clipping, blending, and transparency.
"""

from __future__ import annotations

import hashlib
import logging
import math
import threading
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)


class RenderQuality(IntEnum):
    """Rendering quality presets that trade speed for fidelity."""
    DRAFT = 0
    NORMAL = 1
    HIGH = 2
    ULTRA = 3


class RenderingIntent(Enum):
    """Standard ICC rendering intents."""
    PERCEPTUAL = 0
    RELATIVE_COLORIMETRIC = 1
    SATURATION = 2
    ABSOLUTE_COLORIMETRIC = 3


class BlendMode(Enum):
    """PDF blend modes for transparency compositing."""
    NORMAL = "Normal"
    MULTIPLY = "Multiply"
    SCREEN = "Screen"
    OVERLAY = "Overlay"
    DARKEN = "Darken"
    LIGHTEN = "Lighten"
    COLOR_DODGE = "ColorDodge"
    COLOR_BURN = "ColorBurn"
    HARD_LIGHT = "HardLight"
    SOFT_LIGHT = "SoftLight"
    DIFFERENCE = "Difference"
    EXCLUSION = "Exclusion"
    HUE = "Hue"
    SATURATION = "Saturation"
    COLOR = "Color"
    LUMINOSITY = "Luminosity"


@dataclass
class Viewport:
    """Defines a rectangular region of a page to render."""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    def is_full_page(self, page_width: float, page_height: float) -> bool:
        return (
            self.x == 0.0
            and self.y == 0.0
            and abs(self.width - page_width) < 0.01
            and abs(self.height - page_height) < 0.01
        )

    def to_rect(self) -> fitz.Rect:
        return fitz.Rect(self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class RenderOptions:
    """Configuration for PDF page rendering."""
    dpi: int = 150
    quality: RenderQuality = RenderQuality.NORMAL
    viewport: Optional[Viewport] = None
    rendering_intent: RenderingIntent = RenderingIntent.RELATIVE_COLORIMETRIC
    overprint: bool = False
    blend_mode: BlendMode = BlendMode.NORMAL
    alpha: float = 1.0
    ignore_text: bool = False
    ignore_images: bool = False
    ignore_paths: bool = False
    skip_redacted: bool = True
    use_acceleration: bool = True
    force_halftone: bool = False

    @property
    def zoom(self) -> float:
        return self.dpi / 72.0

    def validate(self) -> None:
        if not 1 <= self.dpi <= 600:
            raise ValueError(f"DPI must be between 1 and 600, got {self.dpi}")
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError(f"Alpha must be between 0.0 and 1.0, got {self.alpha}")

    def fitz_matrix(self) -> fitz.Matrix:
        return fitz.Matrix(self.zoom, self.zoom)

    @property
    def cache_key(self) -> str:
        parts = [
            str(self.dpi),
            str(self.quality),
            str(self.viewport.x if self.viewport else 0),
            str(self.viewport.y if self.viewport else 0),
            str(self.viewport.width if self.viewport else 0),
            str(self.viewport.height if self.viewport else 0),
            str(self.rendering_intent.value),
            str(self.overprint),
            str(self.blend_mode.value),
            f"{self.alpha:.2f}",
        ]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


@dataclass
class GraphicsState:
    """Snapshot of the PDF graphics state for save/restore."""
    ctm: Tuple[float, ...] = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    fill_color: Tuple[float, ...] = (0.0, 0.0, 0.0)
    stroke_color: Tuple[float, ...] = (0.0, 0.0, 0.0)
    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0
    line_width: float = 1.0
    line_cap: int = 0
    line_join: int = 0
    miter_limit: float = 10.0
    dash_pattern: Tuple[float, ...] = ()
    dash_phase: float = 0.0
    blend_mode: BlendMode = BlendMode.NORMAL
    clipping_rect: Optional[fitz.Rect] = None
    font_size: float = 12.0
    text_leading: float = 0.0
    text_rendering_mode: int = 0
    char_spacing: float = 0.0
    word_spacing: float = 0.0
    horizontal_scaling: float = 100.0


@dataclass
class CachedPage:
    """A cached rendered page with metadata."""
    image: Image.Image
    page_number: int
    render_options_hash: str
    width: int
    height: int
    timestamp: float = 0.0

    @property
    def size_bytes(self) -> int:
        import sys
        return sys.getsizeof(self.image.tobytes())


class RenderCache:
    """Thread-safe LRU cache for rendered page images.

    Prevents redundant re-rendering of pages with identical options and
    manages memory pressure by evicting least-recently-used entries.
    """

    def __init__(self, max_entries: int = 32, max_bytes: int = 512 * 1024 * 1024):
        self._max_entries = max_entries
        self._max_bytes = max_bytes
        self._cache: Dict[str, CachedPage] = {}
        self._access_order: List[str] = []
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, doc_id: str, page_number: int, options: RenderOptions) -> Optional[Image.Image]:
        key = self._make_key(doc_id, page_number, options)
        with self._lock:
            entry = self._cache.get(key)
            if entry is not None:
                self._hits += 1
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return entry.image.copy()
            self._misses += 1
            return None

    def put(self, doc_id: str, page_number: int, options: RenderOptions, image: Image.Image) -> None:
        key = self._make_key(doc_id, page_number, options)
        import time
        entry = CachedPage(
            image=image.copy(),
            page_number=page_number,
            render_options_hash=options.cache_key,
            width=image.width,
            height=image.height,
            timestamp=time.time(),
        )
        with self._lock:
            self._cache[key] = entry
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            self._evict_if_needed()

    def invalidate(self, doc_id: Optional[str] = None, page_number: Optional[int] = None) -> int:
        with self._lock:
            if doc_id is None and page_number is None:
                count = len(self._cache)
                self._cache.clear()
                self._access_order.clear()
                return count
            keys_to_remove = []
            for key in list(self._cache.keys()):
                parts = key.split(":")
                if doc_id and parts[0] != doc_id:
                    continue
                if page_number is not None and int(parts[1]) != page_number:
                    continue
                keys_to_remove.append(key)
            for key in keys_to_remove:
                self._cache.pop(key, None)
                if key in self._access_order:
                    self._access_order.remove(key)
            return len(keys_to_remove)

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "entries": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
                "size_bytes": sum(e.size_bytes for e in self._cache.values()),
            }

    def _evict_if_needed(self) -> None:
        while len(self._cache) > self._max_entries:
            if not self._access_order:
                break
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)
        total_size = sum(e.size_bytes for e in self._cache.values())
        while total_size > self._max_bytes and self._access_order:
            oldest_key = self._access_order.pop(0)
            removed = self._cache.pop(oldest_key, None)
            if removed:
                total_size -= removed.size_bytes

    @staticmethod
    def _make_key(doc_id: str, page_number: int, options: RenderOptions) -> str:
        return f"{doc_id}:{page_number}:{options.cache_key}"


class GraphicsStateStack:
    """Manages the graphics state stack for save/restore operations."""

    def __init__(self, initial: Optional[GraphicsState] = None):
        self._stack: List[GraphicsState] = []
        self._current = initial or GraphicsState()

    @property
    def current(self) -> GraphicsState:
        return self._current

    def save(self) -> None:
        import copy
        self._stack.append(copy.deepcopy(self._current))

    def restore(self) -> GraphicsState:
        if not self._stack:
            logger.warning("Graphics state restore with empty stack")
            return self._current
        self._current = self._stack.pop()
        return self._current

    def modify(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if hasattr(self._current, key):
                setattr(self._current, key, value)
            else:
                logger.warning("Unknown graphics state attribute: %s", key)

    @property
    def depth(self) -> int:
        return len(self._stack)


class SoftwareRenderer:
    """Renders PDF pages to PIL Images using PyMuPDF as the rendering backend.

    Provides configurable DPI, viewport clipping, graphics state management,
    and an LRU cache to avoid redundant renders. All heavy lifting is delegated
    to fitz (PyMuPDF) for native-speed rasterization while the surrounding
    orchestration, caching, and color handling are pure Python.
    """

    def __init__(self, cache: Optional[RenderCache] = None):
        self._cache = cache or RenderCache()
        self._graphics_stacks: Dict[str, GraphicsStateStack] = {}

    def render_page(
        self,
        doc: fitz.Document,
        page_number: int,
        options: Optional[RenderOptions] = None,
    ) -> Image.Image:
        options = options or RenderOptions()
        options.validate()

        doc_id = self._document_id(doc)
        cached = self._cache.get(doc_id, page_number, options)
        if cached is not None:
            logger.debug("Cache hit for page %d", page_number)
            return cached

        image = self._render_page_internal(doc, page_number, options)
        self._cache.put(doc_id, page_number, options, image)
        return image

    def render_viewport(
        self,
        doc: fitz.Document,
        page_number: int,
        viewport: Viewport,
        dpi: int = 150,
    ) -> Image.Image:
        options = RenderOptions(dpi=dpi, viewport=viewport)
        return self.render_page(doc, page_number, options)

    def render_pages(
        self,
        doc: fitz.Document,
        page_numbers: Sequence[int],
        options: Optional[RenderOptions] = None,
        callback: Optional[callable] = None,
    ) -> Dict[int, Image.Image]:
        results: Dict[int, Image.Image] = {}
        total = len(page_numbers)
        for idx, page_num in enumerate(page_numbers):
            results[page_num] = self.render_page(doc, page_num, options)
            if callback:
                callback(idx + 1, total, page_num)
        return results

    def invalidate_cache(
        self,
        doc: Optional[fitz.Document] = None,
        page_number: Optional[int] = None,
    ) -> int:
        doc_id = self._document_id(doc) if doc else None
        return self._cache.invalidate(doc_id, page_number)

    def get_graphics_state(self, doc_id: str) -> GraphicsStateStack:
        if doc_id not in self._graphics_stacks:
            self._graphics_stacks[doc_id] = GraphicsStateStack()
        return self._graphics_stacks[doc_id]

    def clear_graphics_states(self, doc_id: Optional[str] = None) -> None:
        if doc_id:
            self._graphics_stacks.pop(doc_id, None)
        else:
            self._graphics_stacks.clear()

    @property
    def cache_stats(self) -> Dict[str, Any]:
        return self._cache.stats

    def _render_page_internal(
        self,
        doc: fitz.Document,
        page_number: int,
        options: RenderOptions,
    ) -> Image.Image:
        if page_number < 0 or page_number >= len(doc):
            raise IndexError(
                f"Page number {page_number} out of range for document with {len(doc)} pages"
            )

        page = doc[page_number]
        mat = options.fitz_matrix()

        if options.viewport and not options.viewport.is_full_page(
            page.rect.width, page.rect.height
        ):
            clip = options.viewport.to_rect()
            clip = clip & page.rect
            if clip.is_empty or clip.is_infinite:
                raise ValueError("Viewport does not intersect with page")
            pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        else:
            flags = self._build_fitz_flags(options)
            pix = page.get_pixmap(matrix=mat, alpha=False, flags=flags)

        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        if options.alpha < 1.0:
            image = self._apply_global_alpha(image, options.alpha)

        return image

    @staticmethod
    def _build_fitz_flags(options: RenderOptions) -> int:
        flags = 0
        if options.ignore_text:
            flags |= fitz.PDF_IGNORE_TEXT
        if not options.use_acceleration:
            flags |= fitz.PDF_NO_CACHE
        if options.force_halftone:
            flags |= fitz.PDF_FORCE_HALFTONE
        return flags

    @staticmethod
    def _apply_global_alpha(image: Image.Image, alpha: float) -> Image.Image:
        if alpha >= 1.0:
            return image
        rgba = image.convert("RGBA")
        alpha_channel = rgba.split()[3]
        scaled = alpha_channel.point(lambda p: int(p * alpha))
        rgba.putalpha(scaled)
        return rgba.convert("RGB")

    @staticmethod
    def _document_id(doc: fitz.Document) -> str:
        try:
            return doc.name or str(id(doc))
        except Exception:
            return str(id(doc))

    def render_page_region(
        self,
        doc: fitz.Document,
        page_number: int,
        region_x: int,
        region_y: int,
        region_width: int,
        region_height: int,
        dpi: int = 150,
    ) -> Image.Image:
        page = doc[page_number]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        clip = fitz.Rect(
            region_x / zoom,
            region_y / zoom,
            (region_x + region_width) / zoom,
            (region_y + region_height) / zoom,
        )
        clip = clip & page.rect
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def render_text_overlay(
        self,
        doc: fitz.Document,
        page_number: int,
        search_rect: fitz.Rect,
        color: Tuple[int, int, int] = (255, 255, 0),
        dpi: int = 150,
    ) -> Image.Image:
        page = doc[page_number]
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

        zoom = dpi / 72.0
        scaled_rect = fitz.Rect(
            search_rect.x0 * zoom,
            search_rect.y0 * zoom,
            search_rect.x1 * zoom,
            search_rect.y1 * zoom,
        )

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(overlay)
        draw.rectangle(
            [scaled_rect.x0, scaled_rect.y0, scaled_rect.x1, scaled_rect.y1],
            fill=(*color, 100),
        )
        image_rgba = image.convert("RGBA")
        composited = Image.alpha_composite(image_rgba, overlay)
        return composited.convert("RGB")

    def get_page_dimensions(
        self, doc: fitz.Document, page_number: int, dpi: int = 72
    ) -> Tuple[int, int]:
        page = doc[page_number]
        zoom = dpi / 72.0
        width = int(page.rect.width * zoom)
        height = int(page.rect.height * zoom)
        return width, height

    def extract_page_links(
        self, doc: fitz.Document, page_number: int
    ) -> List[Dict[str, Any]]:
        page = doc[page_number]
        links = page.get_links()
        result = []
        for link in links:
            entry: Dict[str, Any] = {
                "kind": link.get("kind", 0),
                "rect": {
                    "x0": link["from"].x0,
                    "y0": link["from"].y0,
                    "x1": link["from"].x1,
                    "y1": link["from"].y1,
                },
            }
            uri = link.get("uri")
            if uri:
                entry["uri"] = uri
            page_dest = link.get("page")
            if page_dest is not None:
                entry["dest_page"] = page_dest
            result.append(entry)
        return result

    def render_page_with_annotations(
        self,
        doc: fitz.Document,
        page_number: int,
        options: Optional[RenderOptions] = None,
        show_annotations: bool = True,
    ) -> Image.Image:
        image = self.render_page(doc, page_number, options)
        if not show_annotations:
            return image

        page = doc[page_number]
        annotations = list(page.annots()) if page.annots() else []
        if not annotations:
            return image

        opts = options or RenderOptions()
        zoom = opts.zoom
        rgba = image.convert("RGBA")
        overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(overlay)

        for annot in annotations:
            rect = annot.rect
            scaled = fitz.Rect(
                rect.x0 * zoom, rect.y0 * zoom, rect.x1 * zoom, rect.y1 * zoom
            )
            annot_type = annot.type[0]
            if annot_type == fitz.PDF_ANNOT_HIGHLIGHT:
                draw.rectangle(
                    [scaled.x0, scaled.y0, scaled.x1, scaled.y1],
                    fill=(255, 255, 0, 80),
                )
            elif annot_type == fitz.PDF_ANNOT_UNDERLINE:
                y_line = scaled.y1 - 2
                draw.line(
                    [(scaled.x0, y_line), (scaled.x1, y_line)],
                    fill=(0, 0, 255, 180),
                    width=2,
                )
            elif annot_type == fitz.PDF_ANNOT_STAMP:
                draw.rectangle(
                    [scaled.x0, scaled.y0, scaled.x1, scaled.y1],
                    outline=(255, 0, 0, 180),
                    width=2,
                )

        composited = Image.alpha_composite(rgba, overlay)
        return composited.convert("RGB")

    def compute_rendering_stats(
        self, doc: fitz.Document, page_number: int
    ) -> Dict[str, Any]:
        page = doc[page_number]
        text_dict = page.get_text("dict")
        total_chars = 0
        total_images = 0
        total_paths = 0

        for block in text_dict.get("blocks", []):
            if block["type"] == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        total_chars += len(span.get("text", ""))
            elif block["type"] == 1:
                total_images += 1

        drawings = page.get_drawings()
        total_paths = len(drawings)

        return {
            "page_number": page_number,
            "width": page.rect.width,
            "height": page.rect.height,
            "total_chars": total_chars,
            "total_images": total_images,
            "total_paths": total_paths,
            "rotation": page.rotation,
        }
