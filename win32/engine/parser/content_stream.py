"""PDF content stream decoder.

Parses raw content-stream bytes into a list of :class:`ContentBlock`
objects (text, image, path) using the operator grammar defined in the PDF
specification.  Tracks the full graphics state stack (CTM, colour, line
width, text matrix, font, etc.) throughout.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .object_model import (
    ContentBlock,
    ImageBlock,
    ObjectType,
    PathBlock,
    PathSegment,
    TextBlock,
)


# ---------------------------------------------------------------------------
# Graphics-state snapshot
# ---------------------------------------------------------------------------

@dataclass
class _GState:
    """Internal graphics-state record kept on a stack."""

    ctm: List[float] = field(default_factory=lambda: [1, 0, 0, 1, 0, 0])
    text_matrix: List[float] = field(default_factory=lambda: [1, 0, 0, 1, 0, 0])
    text_line_matrix: List[float] = field(default_factory=lambda: [1, 0, 0, 1, 0, 0])
    font_name: str = ""
    font_size: float = 0.0
    char_spacing: float = 0.0
    word_spacing: float = 0.0
    text_horiz_scale: float = 1.0
    leading: float = 0.0
    rendering_mode: int = 0
    text_rise: float = 0.0

    fill_color: Tuple[float, ...] = (0.0,)
    stroke_color: Tuple[float, ...] = (0.0,)
    fill_cs: str = "DeviceGray"
    stroke_cs: str = "DeviceGray"

    line_width: float = 1.0
    line_cap: int = 0
    line_join: int = 0
    miter_limit: float = 10.0
    dash: Tuple[float, ...] = ()
    flatness: float = 1.0

    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0
    blend_mode: str = "Normal"
    smoothness: float = 0.0

    rendering_intent: str = "RelativeColorimetric"
    stroke_adjust: bool = False
    overprint_fill: bool = False
    overprint_stroke: bool = False

    def clone(self) -> "_GState":
        import copy
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Utility – 2D matrix helpers
# ---------------------------------------------------------------------------

def _mmultiply(a: List[float], b: List[float]) -> List[float]:
    """Multiply two 3×3 affine matrices (column-major, a0..a5 form)."""
    # Convert [a,b,c,d,e,f] ↔ 3×3
    # | a  b  0 |   | b0 b1 0 |
    # | c  d  0 | × | b2 b3 0 |
    # | e  f  1 |   | b4 b5 1 |
    a0, a1, a2, a3, a4, a5 = a
    b0, b1, b2, b3, b4, b5 = b
    return [
        a0 * b0 + a1 * b2,
        a0 * b1 + a1 * b3,
        a2 * b0 + a3 * b2,
        a2 * b1 + a3 * b3,
        a4 * b0 + a5 * b2 + b4,
        a4 * b1 + a5 * b3 + b5,
    ]


def _transform_point(m: List[float], x: float, y: float) -> Tuple[float, float]:
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def _apply_ctm(state: _GState, x: float, y: float) -> Tuple[float, float]:
    return _transform_point(state.ctm, x, y)


def _text_pos(state: _GState) -> Tuple[float, float]:
    """Current text cursor in user space."""
    tm = state.text_matrix
    ctm = state.ctm
    m = _mmultiply(ctm, tm)
    return (m[4], m[5])


def _move_text(state: _GState, dx: float, dy: float) -> None:
    """Advance the text matrix by (dx, dy) in text space."""
    tm = state.text_matrix
    state.text_matrix = [
        tm[0], tm[1], tm[2], tm[3],
        tm[0] * dx + tm[2] * dy + tm[4],
        tm[1] * dx + tm[3] * dy + tm[5],
    ]


def _set_text_matrix(
    state: _GState, a: float, b: float, c: float, d: float, e: float, f: float
) -> None:
    state.text_matrix = [a, b, c, d, e, f]
    state.text_line_matrix = [a, b, c, d, e, f]


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _parse_color(
    tokens: List[str], cs: str, start: int
) -> Tuple[Tuple[float, ...], str, int]:
    """Read colour components from *tokens* given a colourspace name."""
    n = {"DeviceGray": 1, "DeviceRGB": 3, "DeviceCMYK": 4}.get(cs, 1)
    vals: List[float] = []
    i = start
    while len(vals) < n and i < len(tokens):
        try:
            vals.append(float(tokens[i]))
        except ValueError:
            break
        i += 1
    return tuple(vals), cs, i


# ---------------------------------------------------------------------------
# ContentStreamDecoder
# ---------------------------------------------------------------------------

class ContentStreamDecoder:
    """Decode a PDF content stream into :class:`ContentBlock` objects.

    Parameters
    ----------
    resources : dict
        The page-level resource dictionary (fonts, xobjects, colour spaces)
        as a raw PDF object string – used to resolve ``Do`` image references.
    font_map : dict, optional
        ``{resource_name: PDFFont}`` mapping for font lookups.
    """

    def __init__(
        self,
        resources: str = "",
        font_map: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._resources = resources
        self._font_map: Dict[str, str] = font_map or {}
        self._state = _GState()
        self._state_stack: List[_GState] = []
        self._blocks: List[ContentBlock] = []
        self._path_segments: List[PathSegment] = []
        self._path_current: Optional[Tuple[float, float]] = None
        self._path_started = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decode(self, stream_bytes: bytes) -> List[ContentBlock]:
        """Decode *stream_bytes* and return the resulting content blocks."""
        if not stream_bytes:
            return []

        try:
            text = stream_bytes.decode("latin-1")
        except Exception:
            text = stream_bytes.decode("utf-8", errors="replace")

        # Tokenise – split on whitespace and parentheses/brackets.
        tokens = self._tokenise(text)
        self._interpret(tokens)
        return self._blocks

    def decode_string(self, text: str) -> List[ContentBlock]:
        """Decode a text content stream already decoded to a string."""
        tokens = self._tokenise(text)
        self._interpret(tokens)
        return self._blocks

    # ------------------------------------------------------------------
    # Tokeniser
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenise(text: str) -> List[str]:
        """Split content stream into tokens (numbers, names, operators, strings)."""
        tokens: List[str] = []
        i = 0
        length = len(text)
        while i < length:
            ch = text[i]

            # Skip whitespace
            if ch in " \t\n\r\x00":
                i += 1
                continue

            # Comment
            if ch == "%":
                while i < length and text[i] != "\n":
                    i += 1
                continue

            # String literal (parentheses)
            if ch == "(":
                j = i + 1
                depth = 1
                buf: List[str] = []
                while j < length and depth > 0:
                    c = text[j]
                    if c == "\\":
                        j += 1
                        if j < length:
                            esc = text[j]
                            if esc == "n":
                                buf.append("\n")
                            elif esc == "r":
                                buf.append("\r")
                            elif esc == "t":
                                buf.append("\t")
                            elif esc == "b":
                                buf.append("\b")
                            elif esc == "f":
                                buf.append("\f")
                            elif esc == "(":
                                buf.append("(")
                            elif esc == ")":
                                buf.append(")")
                            elif esc == "\\":
                                buf.append("\\")
                            elif esc.isdigit():
                                octal = esc
                                for k in range(2):
                                    j += 1
                                    if j < length and text[j].isdigit():
                                        octal += text[j]
                                    else:
                                        break
                                buf.append(chr(int(octal, 8)))
                            else:
                                buf.append(esc)
                    elif c == "(":
                        depth += 1
                        buf.append(c)
                    elif c == ")":
                        depth -= 1
                        if depth > 0:
                            buf.append(c)
                    else:
                        buf.append(c)
                    j += 1
                tokens.append("".join(buf))
                i = j
                continue

            # Hex string
            if ch == "<":
                j = text.index(">", i) if ">" in text[i:] else length - 1
                tokens.append(text[i : j + 1])
                i = j + 1
                continue

            # Name
            if ch == "/":
                j = i + 1
                while j < length and text[j] not in " \t\n\r/<>[]{}()%\x00":
                    j += 1
                tokens.append(text[i:j])
                i = j
                continue

            # Array delimiters – skip over arrays
            if ch in "[":  # noqa: E501
                depth = 1
                j = i + 1
                while j < length and depth > 0:
                    if text[j] == "[":
                        depth += 1
                    elif text[j] == "]":
                        depth -= 1
                    j += 1
                tokens.append(text[i:j])
                i = j
                continue

            if ch == "]":
                tokens.append("]")
                i += 1
                continue

            # Number (integer or real) or negative sign
            if ch.isdigit() or ch == "." or (ch == "-" and i + 1 < length and (text[i + 1].isdigit() or text[i + 1] == ".")):
                j = i + 1
                while j < length and (text[j].isdigit() or text[j] == "."):
                    j += 1
                if j < length and text[j] in "eE":
                    j += 1
                    if j < length and text[j] in "+-":
                        j += 1
                    while j < length and text[j].isdigit():
                        j += 1
                tokens.append(text[i:j])
                i = j
                continue

            # Operator or name
            j = i
            while j < length and text[j] not in " \t\n\r/<>[]{}()%\x00":
                j += 1
            if j > i:
                tokens.append(text[i:j])
            i = j

        return tokens

    # ------------------------------------------------------------------
    # Interpreter
    # ------------------------------------------------------------------

    def _interpret(self, tokens: List[str]) -> None:
        i = 0
        n = len(tokens)
        # Operator precedence: many PDF operators consume preceding tokens.
        while i < n:
            tok = tokens[i]

            # ── Text-object operators ──────────────────────────────────
            if tok == "BT":
                self._state.text_matrix = [1, 0, 0, 1, 0, 0]
                self._state.text_line_matrix = [1, 0, 0, 1, 0, 0]
                i += 1
                continue
            if tok == "ET":
                i += 1
                continue

            # ── Text state operators ──────────────────────────────────
            if tok == "Tf" and i >= 2:
                font_name = tokens[i - 2].lstrip("/")
                try:
                    font_size = float(tokens[i - 1])
                except (ValueError, IndexError):
                    font_size = 0.0
                self._state.font_name = font_name
                self._state.font_size = font_size
                i += 1
                continue

            if tok == "Tc" and i >= 1:
                try:
                    self._state.char_spacing = float(tokens[i - 1])
                except (ValueError, IndexError):
                    pass
                i += 1
                continue

            if tok == "Tw" and i >= 1:
                try:
                    self._state.word_spacing = float(tokens[i - 1])
                except (ValueError, IndexError):
                    pass
                i += 1
                continue

            if tok == "Tz" and i >= 1:
                try:
                    self._state.text_horiz_scale = float(tokens[i - 1]) / 100.0
                except (ValueError, IndexError):
                    pass
                i += 1
                continue

            if tok == "TL" and i >= 1:
                try:
                    self._state.leading = float(tokens[i - 1])
                except (ValueError, IndexError):
                    pass
                i += 1
                continue

            if tok == "Tr" and i >= 1:
                try:
                    self._state.rendering_mode = int(tokens[i - 1])
                except (ValueError, IndexError):
                    pass
                i += 1
                continue

            if tok == "Ts" and i >= 1:
                try:
                    self._state.text_rise = float(tokens[i - 1])
                except (ValueError, IndexError):
                    pass
                i += 1
                continue

            # ── Text positioning operators ─────────────────────────────
            if tok == "Td" and i >= 3:
                try:
                    ty = float(tokens[i - 1])
                    tx = float(tokens[i - 2])
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._state.text_matrix = [
                    self._state.text_line_matrix[0],
                    self._state.text_line_matrix[1],
                    self._state.text_line_matrix[2],
                    self._state.text_line_matrix[3],
                    self._state.text_line_matrix[0] * tx
                    + self._state.text_line_matrix[2] * ty
                    + self._state.text_line_matrix[4],
                    self._state.text_line_matrix[1] * tx
                    + self._state.text_line_matrix[3] * ty
                    + self._state.text_line_matrix[5],
                ]
                self._state.text_line_matrix = list(self._state.text_matrix)
                i += 1
                continue

            if tok == "TD" and i >= 3:
                try:
                    ty = float(tokens[i - 1])
                    tx = float(tokens[i - 2])
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._state.leading = -ty
                self._state.text_matrix = [
                    self._state.text_line_matrix[0],
                    self._state.text_line_matrix[1],
                    self._state.text_line_matrix[2],
                    self._state.text_line_matrix[3],
                    self._state.text_line_matrix[0] * tx
                    + self._state.text_line_matrix[2] * ty
                    + self._state.text_line_matrix[4],
                    self._state.text_line_matrix[1] * tx
                    + self._state.text_line_matrix[3] * ty
                    + self._state.text_line_matrix[5],
                ]
                self._state.text_line_matrix = list(self._state.text_matrix)
                i += 1
                continue

            if tok == "T*":
                _move_text(self._state, 0, -self._state.leading)
                self._state.text_line_matrix = list(self._state.text_matrix)
                i += 1
                continue

            if tok == "Tm" and i >= 7:
                try:
                    f = [float(tokens[k]) for k in range(i - 6, i)]
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._state.text_matrix = f
                self._state.text_line_matrix = list(f)
                i += 1
                continue

            # ── Text-showing operators ─────────────────────────────────
            if tok == "Tj":
                raw = tokens[i - 1] if i >= 1 else ""
                self._emit_text_block(raw)
                i += 1
                continue

            if tok == "TJ" and i >= 1:
                raw = tokens[i - 1]  # array string
                self._emit_text_block(raw)
                i += 1
                continue

            if tok == "'":
                _move_text(self._state, 0, -self._state.leading)
                self._state.text_line_matrix = list(self._state.text_matrix)
                raw = tokens[i - 1] if i >= 1 else ""
                self._emit_text_block(raw)
                i += 1
                continue

            if tok == '"' and i >= 3:
                try:
                    self._state.word_spacing = float(tokens[i - 3])
                    self._state.char_spacing = float(tokens[i - 2])
                except (ValueError, IndexError):
                    pass
                raw = tokens[i - 1] if i >= 1 else ""
                self._emit_text_block(raw)
                i += 1
                continue

            # ── Graphics state operators ───────────────────────────────
            if tok == "q":
                self._state_stack.append(self._state.clone())
                i += 1
                continue

            if tok == "Q":
                if self._state_stack:
                    self._state = self._state_stack.pop()
                i += 1
                continue

            if tok == "cm" and i >= 7:
                try:
                    f = [float(tokens[k]) for k in range(i - 6, i)]
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._state.ctm = _mmultiply(self._state.ctm, f)
                i += 1
                continue

            # ── Colour operators ───────────────────────────────────────
            if tok == "CS" and i >= 1:
                self._state.stroke_cs = tokens[i - 1].lstrip("/")
                i += 1
                continue
            if tok == "cs" and i >= 1:
                self._state.fill_cs = tokens[i - 1].lstrip("/")
                i += 1
                continue

            if tok == "SC" and i >= 2:
                cs = self._state.stroke_cs
                self._state.stroke_color, _, _ = _parse_color(tokens, cs, i - 4)
                i += 1
                continue
            if tok == "sc" and i >= 2:
                cs = self._state.fill_cs
                self._state.fill_color, _, _ = _parse_color(tokens, cs, i - 4)
                i += 1
                continue

            if tok == "SCN" and i >= 2:
                # Handle pattern / shading CS – just grab the numeric components
                cs = self._state.stroke_cs
                self._state.stroke_color, _, _ = _parse_color(tokens, cs, i - 4)
                i += 1
                continue
            if tok == "scn" and i >= 2:
                cs = self._state.fill_cs
                self._state.fill_color, _, _ = _parse_color(tokens, cs, i - 4)
                i += 1
                continue

            if tok == "G" and i >= 1:
                try:
                    v = float(tokens[i - 1])
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._state.fill_color = (v,)
                self._state.stroke_color = (v,)
                i += 1
                continue
            if tok == "g" and i >= 1:
                try:
                    v = float(tokens[i - 1])
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._state.fill_color = (v,)
                i += 1
                continue
            if tok == "RG" and i >= 4:
                try:
                    r, g, b = float(tokens[i - 3]), float(tokens[i - 2]), float(tokens[i - 1])
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._state.fill_color = (r, g, b)
                self._state.stroke_color = (r, g, b)
                i += 1
                continue
            if tok == "rg" and i >= 4:
                try:
                    r, g, b = float(tokens[i - 3]), float(tokens[i - 2]), float(tokens[i - 1])
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._state.fill_color = (r, g, b)
                i += 1
                continue
            if tok == "k" and i >= 5:
                try:
                    c, m, y, k = (
                        float(tokens[i - 4]),
                        float(tokens[i - 3]),
                        float(tokens[i - 2]),
                        float(tokens[i - 1]),
                    )
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._state.fill_color = (c, m, y, k)
                self._state.stroke_color = (c, m, y, k)
                i += 1
                continue
            if tok == "K" and i >= 5:
                try:
                    c, m, y, k = (
                        float(tokens[i - 4]),
                        float(tokens[i - 3]),
                        float(tokens[i - 2]),
                        float(tokens[i - 1]),
                    )
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._state.stroke_color = (c, m, y, k)
                i += 1
                continue
            if tok == "c" and i >= 7:
                try:
                    _ = [float(tokens[k]) for k in range(i - 6, i)]
                except (ValueError, IndexError):
                    i += 1
                    continue
                i += 1
                continue

            # ── Line / path operators ──────────────────────────────────
            if tok == "w" and i >= 1:
                try:
                    self._state.line_width = float(tokens[i - 1])
                except (ValueError, IndexError):
                    pass
                i += 1
                continue

            if tok == "J" and i >= 1:
                try:
                    self._state.line_cap = int(tokens[i - 1])
                except (ValueError, IndexError):
                    pass
                i += 1
                continue

            if tok == "j" and i >= 1:
                try:
                    self._state.line_join = int(tokens[i - 1])
                except (ValueError, IndexError):
                    pass
                i += 1
                continue

            if tok == "M" and i >= 1:
                try:
                    self._state.miter_limit = float(tokens[i - 1])
                except (ValueError, IndexError):
                    pass
                i += 1
                continue

            if tok == "d" and i >= 2:
                dash_tok = tokens[i - 2]
                try:
                    self._state.dash = tuple(
                        float(x) for x in dash_tok.strip("[]").split()
                    )
                except Exception:
                    pass
                i += 1
                continue

            # ── Path construction ──────────────────────────────────────
            if tok == "m" and i >= 3:
                try:
                    y, x = float(tokens[i - 1]), float(tokens[i - 2])
                except (ValueError, IndexError):
                    i += 1
                    continue
                pt = _apply_ctm(self._state, x, y)
                self._path_segments.append(PathSegment(operator="m", points=[pt]))
                self._path_current = pt
                self._path_started = True
                i += 1
                continue

            if tok == "l" and i >= 3:
                try:
                    y, x = float(tokens[i - 1]), float(tokens[i - 2])
                except (ValueError, IndexError):
                    i += 1
                    continue
                pt = _apply_ctm(self._state, x, y)
                self._path_segments.append(PathSegment(operator="l", points=[pt]))
                self._path_current = pt
                i += 1
                continue

            if tok == "c" and i >= 7:
                try:
                    pts = [
                        _apply_ctm(self._state, float(tokens[i - j]), float(tokens[i - j + 1]))
                        for j in range(6, 0, -2)
                    ]
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._path_segments.append(PathSegment(operator="c", points=pts))
                if pts:
                    self._path_current = pts[-1]
                i += 1
                continue

            if tok == "v" and i >= 5:
                try:
                    p1 = _apply_ctm(self._state, float(tokens[i - 4]), float(tokens[i - 3]))
                    p2 = _apply_ctm(self._state, float(tokens[i - 2]), float(tokens[i - 1]))
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._path_segments.append(PathSegment(operator="v", points=[p1, p2]))
                self._path_current = p2
                i += 1
                continue

            if tok == "y" and i >= 5:
                try:
                    p1 = _apply_ctm(self._state, float(tokens[i - 4]), float(tokens[i - 3]))
                    p2 = _apply_ctm(self._state, float(tokens[i - 2]), float(tokens[i - 1]))
                except (ValueError, IndexError):
                    i += 1
                    continue
                self._path_segments.append(PathSegment(operator="y", points=[p1, p2]))
                self._path_current = p2
                i += 1
                continue

            if tok == "h":
                self._path_segments.append(PathSegment(operator="h", points=[]))
                i += 1
                continue

            if tok == "re" and i >= 5:
                try:
                    ry, rx = float(tokens[i - 3]), float(tokens[i - 4])
                    rh, rw = float(tokens[i - 1]), float(tokens[i - 2])
                except (ValueError, IndexError):
                    i += 1
                    continue
                x1, y1 = _apply_ctm(self._state, rx, ry)
                x2, y2 = _apply_ctm(self._state, rx + rw, ry)
                x3, y3 = _apply_ctm(self._state, rx + rw, ry + rh)
                x4, y4 = _apply_ctm(self._state, rx, ry + rh)
                self._path_segments.append(
                    PathSegment(operator="re", points=[(x1, y1), (x2, y2), (x3, y3), (x4, y4)])
                )
                self._path_current = (x1, y1)
                self._path_started = True
                i += 1
                continue

            # ── Path-painting operators ────────────────────────────────
            if tok in ("S", "s", "f", "F", "f*", "B", "B*", "n", "W", "W*"):
                self._emit_path_block(tok)
                i += 1
                continue

            if tok == "b" or tok == "b*":
                self._emit_path_block(tok)
                i += 1
                continue

            # ── XObject ────────────────────────────────────────────────
            if tok == "Do" and i >= 1:
                name = tokens[i - 1].lstrip("/")
                self._emit_xobject(name)
                i += 1
                continue

            # ── ExtGState ──────────────────────────────────────────────
            if tok == "gs" and i >= 1:
                self._apply_ext_gstate(tokens[i - 1].lstrip("/"))
                i += 1
                continue

            # ── Clipping ───────────────────────────────────────────────
            if tok in ("W", "W*"):
                # handled as path-paint above, but standalone clipping
                i += 1
                continue

            # ── Move/line helpers ──────────────────────────────────────
            if tok == "n":
                # End path without fill/stroke
                self._path_segments.clear()
                self._path_current = None
                self._path_started = False
                i += 1
                continue

            # ── Misc / unknown ─────────────────────────────────────────
            i += 1

    # ------------------------------------------------------------------
    # Text block emission
    # ------------------------------------------------------------------

    def _emit_text_block(self, raw: str) -> None:
        """Create a TextBlock from the current graphics state."""
        text = self._extract_string(raw)
        if not text:
            return

        combined = _mmultiply(self._state.ctm, self._state.text_matrix)
        origin = (combined[4], combined[5])

        # Compute approximate bbox
        fs = self._state.font_size
        char_count = len(text) or 1
        approx_width = char_count * fs * 0.6 * self._state.text_horiz_scale
        x0, y0 = origin
        x1 = x0 + approx_width
        y1 = y0 + fs

        # Normalise colour to RGB-ish (0-1 range)
        color = self._normalise_color(self._state.fill_color)

        flags = 0
        if self._state.rendering_mode in (1, 3):
            flags |= 1  # stroke

        tb = TextBlock(
            text=text,
            font_name=self._state.font_name,
            font_size=fs,
            color=color,
            origin=origin,
            bbox=(x0, y0, x1, y1),
            flags=flags,
            char_spacing=self._state.char_spacing,
            word_spacing=self._state.word_spacing,
        )
        self._blocks.append(
            ContentBlock(
                block_type=ObjectType.TEXT,
                text_block=tb,
                bbox=tb.bbox,
            )
        )

    @staticmethod
    def _extract_string(raw: str) -> str:
        """Pull the actual characters out of a PDF string literal or TJ array."""
        if raw.startswith("["):
            # TJ array – concatenate the string elements
            parts: List[str] = []
            for m in re.finditer(r"\(([^)]*)\)", raw):
                parts.append(m.group(1))
            return "".join(parts)
        # Simple string literal
        return raw

    @staticmethod
    def _normalise_color(color: Tuple[float, ...]) -> Tuple[float, float, float]:
        n = len(color)
        if n == 1:
            v = color[0]
            return (v, v, v)
        if n == 3:
            return tuple(color[:3])  # type: ignore[return-value]
        if n == 4:
            c, m, y, k = color
            r = min(1.0, 1.0 - c - k)
            g = min(1.0, 1.0 - m - k)
            b = min(1.0, 1.0 - y - k)
            return (r, g, b)
        return (0.0, 0.0, 0.0)

    # ------------------------------------------------------------------
    # Path block emission
    # ------------------------------------------------------------------

    def _emit_path_block(self, operator: str) -> None:
        if not self._path_segments:
            return

        # Compute bounding box from all path points
        all_pts = []
        for seg in self._path_segments:
            all_pts.extend(seg.points)
        if not all_pts:
            self._path_segments.clear()
            self._path_started = False
            return

        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        bbox = (min(xs), min(ys), max(xs), max(ys))

        fill_color: Optional[Tuple[float, ...]] = None
        stroke_color = self._normalise_color(self._state.stroke_color)

        if operator in ("f", "F", "f*", "B", "B*", "b", "b*"):
            fill_color = self._normalise_color(self._state.fill_color)

        close = operator in ("s", "b", "b*", "f*", "h")

        pb = PathBlock(
            segments=list(self._path_segments),
            stroke_color=stroke_color,
            fill_color=fill_color,
            line_width=self._state.line_width,
            close_path=close,
            bbox=bbox,
        )
        self._blocks.append(
            ContentBlock(
                block_type=ObjectType.PATH,
                path_block=pb,
                bbox=bbox,
            )
        )

        self._path_segments.clear()
        self._path_current = None
        self._path_started = False

    # ------------------------------------------------------------------
    # XObject (image) emission
    # ------------------------------------------------------------------

    def _emit_xobject(self, name: str) -> None:
        """Record an image XObject reference.

        Actual image extraction happens at a higher level; here we only
        emit a placeholder block so positions are preserved.
        """
        ib = ImageBlock(
            name=name,
            bbox=(0, 0, 0, 0),  # refined by caller
        )
        self._blocks.append(
            ContentBlock(
                block_type=ObjectType.IMAGE,
                image_block=ib,
                bbox=(0, 0, 0, 0),
            )
        )

    # ------------------------------------------------------------------
    # ExtGState application
    # ------------------------------------------------------------------

    def _apply_ext_gstate(self, _name: str) -> None:
        """Apply a graphics-state dictionary (stub – full impl needs resource dict)."""
        # In a full implementation this would look up the /ExtGState
        # dictionary from the page resources and apply all entries.
        # For now we record the call without mutation.
        pass


# ---------------------------------------------------------------------------
# Public convenience function
# ---------------------------------------------------------------------------

def decode_content_stream(
    stream_bytes: bytes,
    resources: str = "",
    font_map: Optional[Dict[str, str]] = None,
) -> List[ContentBlock]:
    """One-shot convenience wrapper around :class:`ContentStreamDecoder`."""
    decoder = ContentStreamDecoder(resources=resources, font_map=font_map)
    return decoder.decode(stream_bytes)
