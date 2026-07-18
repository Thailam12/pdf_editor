"""Text layout engine for PDF text measurement, wrapping, and extraction.

Provides character-level position mapping, bidirectional text support,
font fallback, and layout-preserving text extraction.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum, IntFlag
from typing import Any, Dict, List, Optional, Sequence, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class TextDirection(Enum):
    """Script writing direction."""
    LTR = "ltr"
    RTL = "rtl"
    TTB = "ttb"


class BidiClass(Enum):
    """Unicode bidirectional character classes (simplified)."""
    L = "L"
    R = "R"
    AL = "AL"
    AN = "AN"
    EN = "EN"
    ES = "ES"
    CS = "CS"
    ET = "ET"
    NSM = "NSM"
    BN = "BN"
    B = "B"
    S = "S"
    WS = "WS"
    ON = "ON"
    LRE = "LRE"
    RLE = "RLE"
    LRO = "LRO"
    RLO = "RLO"
    PDF = "PDF"
    LRI = "LRI"
    RLI = "RLI"
    FSI = "FSI"
    PDI = "PDI"


BIDI_LEFT_TO_RIGHT_CHARS = set(
    "\u0041-\u005a\u0061-\u007a"  # Basic Latin
    "\u00c0-\u00ff\u0100-\u017f"  # Latin Extended
    "\u0400-\u04ff"               # Cyrillic
    "\u0370-\u03ff"               # Greek
    "\u0590-\u05ff"               # Hebrew (actually RTL)
)

BIDI_RIGHT_TO_LEFT_CHARS = set(
    "\u0590-\u05ff"  # Hebrew
    "\u0600-\u06ff"  # Arabic
    "\u0700-\u074f"  # Syriac
    "\u0780-\u07bf"  # Thaana
    "\u07c0-\u07ff"  # NKo
    "\u08a0-\u08ff"  # Arabic Extended
)


@dataclass
class GlyphInfo:
    """Position and metric data for a single character glyph."""
    char: str
    x: float
    y: float
    width: float
    height: float
    font_size: float
    font_name: str = ""
    flags: int = 0
    origin: Tuple[float, float] = (0.0, 0.0)
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    @property
    def advance_width(self) -> float:
        return self.width

    @property
    def is_space(self) -> bool:
        return self.char.isspace()

    @property
    def bounding_box(self) -> Tuple[float, float, float, float]:
        return (
            self.x,
            self.y - self.height,
            self.x + self.width,
            self.y,
        )


@dataclass
class TextSpan:
    """A run of text sharing the same formatting attributes."""
    text: str
    font_name: str
    font_size: float
    color: Tuple[float, ...] = (0.0, 0.0, 0.0)
    origin: Tuple[float, float] = (0.0, 0.0)
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    flags: int = 0
    chars: List[GlyphInfo] = field(default_factory=list)

    @property
    def is_bold(self) -> bool:
        return bool(self.flags & 2**4)

    @property
    def is_italic(self) -> bool:
        return bool(self.flags & 2**1)

    @property
    def is_monospace(self) -> bool:
        return bool(self.flags & 2**5)

    @property
    def direction(self) -> TextDirection:
        return classify_text_direction(self.text)

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def advance_width(self) -> float:
        if self.chars:
            last = self.chars[-1]
            return (last.x + last.width) - self.origin[0]
        return self.width


@dataclass
class TextLine:
    """A line of text composed of one or more spans."""
    spans: List[TextSpan]
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    baseline_y: float = 0.0

    @property
    def text(self) -> str:
        return "".join(span.text for span in self.spans)

    @property
    def direction(self) -> TextDirection:
        for span in self.spans:
            if span.direction != TextDirection.LTR:
                return span.direction
        return TextDirection.LTR

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def char_count(self) -> int:
        return sum(len(span.text) for span in self.spans)

    def char_at_offset(self, offset: float) -> Optional[int]:
        running_x = self.bbox[0]
        char_index = 0
        for span in self.spans:
            for glyph in span.chars:
                if glyph.x >= offset or running_x + glyph.width >= offset:
                    return char_index
                running_x += glyph.width
                char_index += 1
        return None


@dataclass
class TextBlock:
    """A paragraph or text block composed of lines."""
    lines: List[TextLine]
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    block_type: int = 0  # 0 = text, 1 = image

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    @property
    def direction(self) -> TextDirection:
        for line in self.lines:
            d = line.direction
            if d != TextDirection.LTR:
                return d
        return TextDirection.LTR

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def line_count(self) -> int:
        return len(self.lines)

    @property
    def char_count(self) -> int:
        return sum(line.char_count for line in self.lines)


@dataclass
class WrappedText:
    """Result of text wrapping: original text split into display lines."""
    lines: List[str]
    total_height: float
    max_width: float
    line_heights: List[float] = field(default_factory=list)


def classify_text_direction(text: str) -> TextDirection:
    if not text:
        return TextDirection.LTR
    rtl_count = sum(1 for c in text if c in BIDI_RIGHT_TO_LEFT_CHARS)
    ltr_count = sum(1 for c in text if c.isalpha() and c not in BIDI_RIGHT_TO_LEFT_CHARS)
    if rtl_count > ltr_count:
        return TextDirection.RTL
    return TextDirection.LTR


def bidi_reorder(text: str, direction: TextDirection = TextDirection.LTR) -> str:
    """Apply a simplified Unicode Bidirectional Algorithm.

    For production use this should follow UAX #9 fully. This implementation
    handles the common LTR/RTL mixing cases.
    """
    if not text:
        return text

    has_rtl = any(c in BIDI_RIGHT_TO_LEFT_CHARS for c in text)
    has_ltr = any(c.isalpha() and c not in BIDI_RIGHT_TO_LEFT_CHARS for c in text)

    if not has_rtl or not has_ltr:
        return text

    segments: List[Tuple[str, TextDirection]] = []
    current_chars: List[str] = []
    current_dir: Optional[TextDirection] = None

    for ch in text:
        if ch in BIDI_RIGHT_TO_LEFT_CHARS:
            ch_dir = TextDirection.RTL
        elif ch.isalpha():
            ch_dir = TextDirection.LTR
        else:
            ch_dir = current_dir or TextDirection.LTR

        if current_dir is None or ch_dir == current_dir:
            current_chars.append(ch)
            current_dir = ch_dir
        else:
            segments.append(("".join(current_chars), current_dir))
            current_chars = [ch]
            current_dir = ch_dir

    if current_chars:
        segments.append(("".join(current_chars), current_dir))

    dominant = direction
    result_parts: List[str] = []
    rtl_segments = [s for s in segments if s[1] == TextDirection.RTL]
    ltr_segments = [s for s in segments if s[1] == TextDirection.LTR]

    if dominant == TextDirection.RTL:
        for seg_text, _ in rtl_segments:
            result_parts.append(seg_text[::-1])
        for seg_text, _ in ltr_segments:
            result_parts.append(seg_text)
    else:
        for seg_text, _ in ltr_segments:
            result_parts.append(seg_text)
        for seg_text, _ in rtl_segments:
            result_parts.append(seg_text[::-1])

    return "".join(result_parts)


class FontFallbackChain:
    """Manages an ordered list of fallback fonts for rendering characters
    not present in the primary font."""

    def __init__(self, primary_font: str = "helv", fallbacks: Optional[List[str]] = None):
        self._primary = primary_font
        self._fallbacks = fallbacks or [
            "helv",
            "cour",
            "tiro",
            "hebo",
            "hebi",
        ]
        self._char_cache: Dict[str, str] = {}

    @property
    def primary_font(self) -> str:
        return self._primary

    def select_font(self, char: str, available_fonts: Optional[set] = None) -> str:
        if char in self._char_cache:
            return self._char_cache[char]

        if available_fonts is None:
            available_fonts = set(self._fallbacks)

        for font in [self._primary] + self._fallbacks:
            if font in available_fonts:
                self._char_cache[char] = font
                return font

        self._char_cache[char] = self._primary
        return self._primary

    def add_fallback(self, font_name: str, position: int = -1) -> None:
        if font_name in self._fallbacks:
            return
        if position < 0 or position >= len(self._fallbacks):
            self._fallbacks.append(font_name)
        else:
            self._fallbacks.insert(position, font_name)
        self._char_cache.clear()

    def clear_cache(self) -> None:
        self._char_cache.clear()


class TextMeasurement:
    """Measures text dimensions using PyMuPDF text extraction data."""

    def __init__(self, font_size: float = 12.0):
        self._font_size = font_size

    def measure_span(self, span: TextSpan) -> Tuple[float, float]:
        if not span.text:
            return (0.0, span.font_size)
        text_width = span.advance_width
        text_height = span.font_size
        return (text_width, text_height)

    def measure_line(self, line: TextLine) -> Tuple[float, float]:
        if not line.spans:
            return (0.0, 0.0)
        max_height = 0.0
        total_width = 0.0
        for span in line.spans:
            w, h = self.measure_span(span)
            total_width += w
            max_height = max(max_height, h)
        return (total_width, max_height)

    def measure_block(self, block: TextBlock) -> Tuple[float, float]:
        if not block.lines:
            return (0.0, 0.0)
        max_width = 0.0
        total_height = 0.0
        for line in block.lines:
            w, h = self.measure_line(line)
            max_width = max(max_width, w)
            total_height += h
        return (max_width, total_height)

    def bbox_for_text(
        self, text: str, font_size: float, origin: Tuple[float, float], font_name: str = "helv"
    ) -> Tuple[float, float, float, float]:
        approx_width = len(text) * font_size * 0.6
        x0, y0 = origin
        return (x0, y0 - font_size, x0 + approx_width, y0)


class LineBreaker:
    """Greedy text wrapping with configurable constraints."""

    def __init__(
        self,
        max_width: float,
        max_lines: int = 0,
        font_size: float = 12.0,
        char_spacing: float = 0.0,
        word_spacing: float = 0.0,
        break_long_words: bool = True,
    ):
        self._max_width = max_width
        self._max_lines = max_lines
        self._font_size = font_size
        self._char_spacing = char_spacing
        self._word_spacing = word_spacing
        self._break_long_words = break_long_words

    def wrap_text(self, text: str) -> WrappedText:
        if not text:
            return WrappedText(lines=[""], total_height=0, max_width=0)

        paragraphs = text.split("\n")
        result_lines: List[str] = []
        line_heights: List[float] = []

        for paragraph in paragraphs:
            if not paragraph:
                result_lines.append("")
                line_heights.append(self._font_size)
                continue

            wrapped = self._wrap_paragraph(paragraph)
            result_lines.extend(wrapped)
            line_heights.extend([self._font_size] * len(wrapped))

        total_height = sum(line_heights)
        return WrappedText(
            lines=result_lines,
            total_height=total_height,
            max_width=self._max_width,
            line_heights=line_heights,
        )

    def _wrap_paragraph(self, text: str) -> List[str]:
        words = text.split(" ")
        lines: List[str] = []
        current_line: List[str] = []
        current_width = 0.0

        for word in words:
            word_width = self._measure_word_width(word)
            space_width = self._measure_word_width(" ")

            needed_width = word_width
            if current_line:
                needed_width = space_width + word_width

            if current_width + needed_width <= self._max_width:
                current_line.append(word)
                current_width += needed_width
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    if self._max_lines > 0 and len(lines) >= self._max_lines:
                        last = lines[-1]
                        if len(last) > 3:
                            lines[-1] = last[:-3] + "..."
                        return lines
                if self._break_long_words and word_width > self._max_width:
                    sub_lines = self._break_word(word)
                    lines.extend(sub_lines[:-1])
                    current_line = [sub_lines[-1]] if sub_lines else []
                    current_width = self._measure_word_width(sub_lines[-1]) if sub_lines else 0.0
                else:
                    current_line = [word]
                    current_width = word_width

        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [""]

    def _break_word(self, word: str) -> List[str]:
        if not word:
            return [""]
        lines: List[str] = []
        current = ""
        for char in word:
            test = current + char
            if self._measure_word_width(test) > self._max_width and current:
                lines.append(current)
                current = char
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    def _measure_word_width(self, word: str) -> float:
        base_width = len(word) * self._font_size * 0.6
        spacing = (len(word) - 1) * self._char_spacing if word else 0.0
        return base_width + spacing


class TextLayoutEngine:
    """High-level text layout engine for PDF text operations.

    Combines extraction, measurement, wrapping, bidi, and position mapping
    to provide a complete text handling pipeline.
    """

    def __init__(self, font_fallback: Optional[FontFallbackChain] = None):
        self._font_fallback = font_fallback or FontFallbackChain()
        self._extraction_cache: Dict[str, List[TextBlock]] = {}

    def extract_page_text(
        self,
        page: fitz.Page,
        preserve_layout: bool = True,
    ) -> List[TextBlock]:
        cache_key = f"{page.parent.name}:{page.number}:{preserve_layout}"
        if cache_key in self._extraction_cache:
            return self._extraction_cache[cache_key]

        if preserve_layout:
            text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        else:
            text_dict = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        blocks: List[TextBlock] = []
        for block_data in text_dict.get("blocks", []):
            if block_data["type"] != 0:
                continue
            block = self._parse_block(block_data)
            blocks.append(block)

        self._extraction_cache[cache_key] = blocks
        return blocks

    def extract_page_text_simple(self, page: fitz.Page) -> str:
        return page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)

    def extract_text_with_positions(
        self, page: fitz.Page
    ) -> List[Dict[str, Any]]:
        words = page.get_text("words")
        results = []
        for w in words:
            x0, y0, x1, y1, word_text, block_no, line_no, word_no = w
            results.append({
                "text": word_text,
                "bbox": (x0, y0, x1, y1),
                "block_number": block_no,
                "line_number": line_no,
                "word_number": word_no,
                "direction": classify_text_direction(word_text).value,
            })
        return results

    def extract_chars_with_positions(
        self, page: fitz.Page
    ) -> List[Dict[str, Any]]:
        text_dict = page.get_text("rawdict")
        chars: List[Dict[str, Any]] = []
        for block in text_dict.get("blocks", []):
            if block["type"] != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    origin = span.get("origin", (0, 0))
                    font_size = span.get("size", 12.0)
                    font_name = span.get("font", "")
                    flags = span.get("flags", 0)
                    span_bbox = span.get("bbox", (0, 0, 0, 0))
                    text = span.get("text", "")

                    if not text:
                        continue

                    char_count = len(text)
                    span_width = span_bbox[2] - span_bbox[0]
                    avg_char_width = span_width / char_count if char_count > 0 else 0

                    for i, ch in enumerate(text):
                        char_x = origin[0] + i * avg_char_width
                        char_y = origin[1]
                        chars.append({
                            "char": ch,
                            "x": char_x,
                            "y": char_y,
                            "width": avg_char_width,
                            "height": font_size,
                            "font_name": font_name,
                            "font_size": font_size,
                            "flags": flags,
                            "bbox": (
                                char_x,
                                char_y - font_size,
                                char_x + avg_char_width,
                                char_y,
                            ),
                        })
        return chars

    def wrap_text(
        self,
        text: str,
        max_width: float,
        font_size: float = 12.0,
        max_lines: int = 0,
    ) -> WrappedText:
        breaker = LineBreaker(
            max_width=max_width,
            max_lines=max_lines,
            font_size=font_size,
        )
        return breaker.wrap_text(text)

    def bidi_reorder_text(self, text: str, direction: TextDirection = TextDirection.LTR) -> str:
        return bidi_reorder(text, direction)

    def get_char_position_map(
        self, page: fitz.Page
    ) -> List[Dict[str, Any]]:
        """Build a character-level position map for inline editing.

        Each entry maps a character index to its exact screen position and
        associated formatting, enabling precise cursor placement and
        character-by-character editing.
        """
        chars_data = self.extract_chars_with_positions(page)
        position_map: List[Dict[str, Any]] = []
        global_index = 0

        for char_info in chars_data:
            ch = char_info["char"]
            x = char_info["x"]
            y = char_info["y"]
            width = char_info["width"]
            height = char_info["height"]

            position_map.append({
                "index": global_index,
                "char": ch,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "bbox": char_info["bbox"],
                "font_name": char_info["font_name"],
                "font_size": char_info["font_size"],
                "flags": char_info["flags"],
                "cursor_before": (x, y - height * 0.8),
                "cursor_after": (x + width, y - height * 0.8),
                "is_space": ch.isspace(),
                "is_line_break": ch in ("\n", "\r"),
            })
            global_index += 1

        return position_map

    def find_char_at_position(
        self, page: fitz.Page, x: float, y: float
    ) -> Optional[Dict[str, Any]]:
        position_map = self.get_char_position_map(page)
        best_match: Optional[Dict[str, Any]] = None
        best_distance = float("inf")

        for entry in position_map:
            cx = entry["x"] + entry["width"] / 2
            cy = entry["y"] - entry["height"] / 2
            dist = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
            if dist < best_distance:
                best_distance = dist
                best_match = entry

        if best_match and best_distance < best_match["width"]:
            return best_match
        return None

    def measure_span(self, text: str, font_size: float, font_name: str = "helv") -> Tuple[float, float]:
        measurer = TextMeasurement(font_size)
        span = TextSpan(
            text=text,
            font_name=font_name,
            font_size=font_size,
            origin=(0.0, font_size),
        )
        return measurer.measure_span(span)

    def clear_cache(self) -> None:
        self._extraction_cache.clear()
        self._font_fallback.clear_cache()

    def _parse_block(self, block_data: Dict[str, Any]) -> TextBlock:
        lines: List[TextLine] = []
        for line_data in block_data.get("lines", []):
            spans = self._parse_spans(line_data)
            line_bbox = tuple(line_data.get("bbox", (0, 0, 0, 0)))
            baseline_y = line_bbox[3] if line_bbox else 0.0
            text_line = TextLine(
                spans=spans,
                bbox=line_bbox,
                baseline_y=baseline_y,
            )
            lines.append(text_line)

        block_bbox = tuple(block_data.get("bbox", (0, 0, 0, 0)))
        return TextBlock(lines=lines, bbox=block_bbox, block_type=block_data.get("type", 0))

    def _parse_spans(self, line_data: Dict[str, Any]) -> List[TextSpan]:
        spans: List[TextSpan] = []
        for span_data in line_data.get("spans", []):
            text = span_data.get("text", "")
            font_name = span_data.get("font", "helv")
            font_size = span_data.get("size", 12.0)
            color_int = span_data.get("color", 0)
            flags = span_data.get("flags", 0)
            origin = span_data.get("origin", (0, 0))
            bbox = tuple(span_data.get("bbox", (0, 0, 0, 0)))

            r = ((color_int >> 16) & 0xFF) / 255.0
            g = ((color_int >> 8) & 0xFF) / 255.0
            b = (color_int & 0xFF) / 255.0

            glyphs: List[GlyphInfo] = []
            char_count = len(text)
            span_width = bbox[2] - bbox[0]
            avg_width = span_width / char_count if char_count > 0 else 0

            for i, ch in enumerate(text):
                gx = origin[0] + i * avg_width
                gy = origin[1]
                glyphs.append(GlyphInfo(
                    char=ch,
                    x=gx,
                    y=gy,
                    width=avg_width,
                    height=font_size,
                    font_size=font_size,
                    font_name=font_name,
                    flags=flags,
                    origin=origin,
                    bbox=(gx, gy - font_size, gx + avg_width, gy),
                ))

            spans.append(TextSpan(
                text=text,
                font_name=font_name,
                font_size=font_size,
                color=(r, g, b),
                origin=origin,
                bbox=bbox,
                flags=flags,
                chars=glyphs,
            ))
        return spans

    def select_fallback_font(self, char: str, available_fonts: Optional[set] = None) -> str:
        return self._font_fallback.select_font(char, available_fonts)
