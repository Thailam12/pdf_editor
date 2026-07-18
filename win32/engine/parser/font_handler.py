"""Font parser and character-code-to-Unicode mapper.

Uses PyMuPDF (fitz) for low-level font access while exposing a clean
interface that the rest of the engine can consume.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import fitz

from .object_model import FontType, PDFFont


# ---------------------------------------------------------------------------
# Well-known PDF font-name → standard-family mapping
# ---------------------------------------------------------------------------

_FAMILY_MAP: Dict[str, str] = {
    # Times
    "TimesNewRoman": "Times New Roman",
    "TimesNewRomanPS": "Times New Roman",
    "Times-Roman": "Times New Roman",
    "Times-Bold": "Times New Roman",
    "Times-Italic": "Times New Roman",
    "Times-BoldItalic": "Times New Roman",
    "TNR": "Times New Roman",
    # Helvetica / Arial
    "Helvetica": "Helvetica",
    "Helvetica-Bold": "Helvetica",
    "Helvetica-Oblique": "Helvetica",
    "Helvetica-BoldOblique": "Helvetica",
    "Arial": "Helvetica",
    "ArialMT": "Helvetica",
    "Arial-Bold": "Helvetica",
    "Arial-Italic": "Helvetica",
    "Arial-BoldItalic": "Helvetica",
    # Courier
    "Courier": "Courier",
    "Courier-Bold": "Courier",
    "Courier-Oblique": "Courier",
    "Courier-BoldOblique": "Courier",
    "CourierNew": "Courier",
    "CourierNewPS": "Courier",
    "Consolas": "Courier",
    # Symbol / Zapf
    "Symbol": "Symbol",
    "ZapfDingbats": "ZapfDingbats",
    # Palatino
    "Palatino-Roman": "Palatino",
    "Palatino-Bold": "Palatino",
    "Palatino-Italic": "Palatino",
    "Palatino-BoldItalic": "Palatino",
    "PalatinoLinotype": "Palatino",
    # Georgia
    "Georgia": "Georgia",
    "Georgia-Bold": "Georgia",
    "Georgia-Italic": "Georgia",
    # Bookman
    "Bookman-Demi": "Bookman",
    "Bookman-Light": "Bookman",
    # Century
    "CenturySchlbk-Bold": "Century Schoolbook",
    "CenturySchlbk-Italic": "Century Schoolbook",
    "CenturySchlbk-BoldItalic": "Century Schoolbook",
    # Avant Garde
    "AvantGarde-Demi": "Avant Garde",
    "AvantGarde-Book": "Avant Garde",
    # Nimbus
    "NimbusRoman": "Times New Roman",
    "NimbusRoman-Bold": "Times New Roman",
    "NimbusSans": "Helvetica",
    "NimbusSans-Bold": "Helvetica",
    "NimbusMonoPS": "Courier",
    # Liberation
    "LiberationSerif": "Times New Roman",
    "LiberationSans": "Helvetica",
    "LiberationMono": "Courier",
    # DejaVu
    "DejaVuSans": "Helvetica",
    "DejaVuSans-Bold": "Helvetica",
    "DejaVuSerif": "Times New Roman",
    "DejaVuSerif-Bold": "Times New Roman",
    "DejaVuSansMono": "Courier",
    # Calibri / Cambria (Windows)
    "Calibri": "Helvetica",
    "Cambria": "Times New Roman",
}

# PDF standard font type-1 base-14 names
_BASE14 = {
    "Courier",
    "Courier-Bold",
    "Courier-Oblique",
    "Courier-BoldOblique",
    "Helvetica",
    "Helvetica-Bold",
    "Helvetica-Oblique",
    "Helvetica-BoldOblique",
    "Times-Roman",
    "Times-Bold",
    "Times-Italic",
    "Times-BoldItalic",
    "Symbol",
    "ZapfDingbats",
}


# ---------------------------------------------------------------------------
# FontHandler
# ---------------------------------------------------------------------------

class FontHandler:
    """Parses font dictionaries and provides character-code mapping."""

    def __init__(self, doc: fitz.Document) -> None:
        self._doc = doc
        self._cache: Dict[int, PDFFont] = {}
        self._unicode_cmap_cache: Dict[int, Dict[int, str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_font(self, xref: int) -> PDFFont:
        """Parse a font object identified by its xref number."""
        if xref in self._cache:
            return self._cache[xref]

        font = PDFFont(ref=xref)
        try:
            obj = self._doc.xref_object(xref, compressed=False)
        except Exception:
            self._cache[xref] = font
            return font

        font.name = self._get_key(obj, "/Name", default="")
        font.base_font = self._get_key(obj, "/BaseFont", default="")
        subtype = self._get_key(obj, "/Subtype", default="")

        # ---- Font type ----
        font.font_type = self._resolve_type(subtype, obj)

        # ---- Encoding ----
        font.encoding = self._get_encoding(obj)
        font.differences = self._get_differences(obj)

        # ---- Descriptor ----
        desc_xref = self._get_dict_xref(obj, "/FontDescriptor")
        if desc_xref:
            self._parse_descriptor(desc_xref, font)

        # ---- Widths ----
        self._parse_widths(obj, font)

        # ---- Embedded check ----
        font.embedded = self._is_embedded(obj, desc_xref)

        # ---- Subset detection ----
        font.subset = self._detect_subset(font.base_font)

        # ---- ToUnicode ----
        touni_xref = self._get_dict_xref(obj, "/ToUnicode")
        if touni_xref:
            font.ToUnicode = self._read_stream(touni_xref)

        # ---- Family mapping ----
        font.family = self._map_family(font.base_font)

        self._cache[xref] = font
        return font

    def get_unicode_cmap(self, font_xref: int) -> Dict[int, str]:
        """Return a ``{character_code: unicode_char}`` map for *font_xref*."""
        if font_xref in self._unicode_cmap_cache:
            return self._unicode_cmap_cache[font_xref]

        cmap: Dict[int, str] = {}
        try:
            obj = self._doc.xref_object(font_xref, compressed=False)
        except Exception:
            self._unicode_cmap_cache[font_xref] = cmap
            return cmap

        touni_xref = self._get_dict_xref(obj, "/ToUnicode")
        if touni_xref:
            stream = self._read_stream(touni_xref)
            if stream:
                cmap = self._parse_cmap(stream)

        self._unicode_cmap_cache[font_xref] = cmap
        return cmap

    def map_char_codes(
        self,
        char_codes: Sequence[int],
        font_xref: int,
    ) -> str:
        """Convert a sequence of character codes to a Unicode string."""
        cmap = self.get_unicode_cmap(font_xref)
        parts: List[str] = []
        for code in char_codes:
            if code in cmap:
                parts.append(cmap[code])
            else:
                parts.append(chr(code) if code < 256 else "?")
        return "".join(parts)

    def parse_all_fonts(self) -> Dict[str, PDFFont]:
        """Parse every font in the document and return ``{name: PDFFont}``."""
        fonts: Dict[str, PDFFont] = {}
        try:
            xref_len = self._doc.xref_length()
        except Exception:
            return fonts

        for xref in range(1, xref_len):
            try:
                obj_type = self._doc.xref_get_key(xref, "Type")
            except Exception:
                continue
            if obj_type[1] != "/Font":
                continue
            font = self.parse_font(xref)
            key = font.name or font.base_font or f"font_{xref}"
            fonts[key] = font
        return fonts

    # ------------------------------------------------------------------
    # Internal helpers – object dictionary access
    # ------------------------------------------------------------------

    @staticmethod
    def _get_key(obj: str, key: str, default: str = "") -> str:
        """Extract a simple value from a raw PDF object string."""
        pattern = re.compile(re.escape(key) + r"\s+(.+?)(?:\s*/|\s*>>)")
        m = pattern.search(obj)
        if m:
            val = m.group(1).strip()
            if val.startswith("/"):
                val = val[1:]
            return val
        return default

    @staticmethod
    def _get_dict_xref(obj: str, key: str) -> Optional[int]:
        """Return the xref of a dictionary referenced by *key*, or None."""
        pattern = re.compile(re.escape(key) + r"\s+(\d+)\s+\d+\s+R")
        m = pattern.search(obj)
        if m:
            return int(m.group(1))
        return None

    # ------------------------------------------------------------------
    # Internal helpers – type / encoding / differences
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_type(subtype: str, obj: str) -> FontType:
        mapping: Dict[str, FontType] = {
            "Type0": FontType.TYPE0,
            "Type1": FontType.TYPE1,
            "Type3": FontType.TYPE3,
            "TrueType": FontType.TRUETYPE,
            "CIDFontType0": FontType.CID_FONT,
            "CIDFontType2": FontType.CID_FONT,
        }
        if subtype in mapping:
            return mapping[subtype]
        if "FontType" in obj:
            return FontType.TYPE1
        return FontType.UNKNOWN

    def _get_encoding(self, obj: str) -> str:
        """Return the encoding name from the font dictionary."""
        enc = self._get_key(obj, "/Encoding")
        if enc:
            return enc
        if "/Differences" in obj:
            return "Differences"
        if "/ToUnicode" in obj:
            return "Unicode"
        return "Standard"

    def _get_differences(self, obj: str) -> List[Tuple[int, str]]:
        """Parse an ``/Encoding`` ``/Differences`` array."""
        diffs: List[Tuple[int, str]] = []
        m = re.search(r"/Differences\s*\[(.+?)\]", obj, re.DOTALL)
        if not m:
            return diffs

        raw = m.group(1)
        tokens = raw.split()
        current_code = 0
        for tok in tokens:
            tok = tok.strip()
            if not tok:
                continue
            if tok.isdigit() or (tok.startswith("-") and tok[1:].isdigit()):
                current_code = int(tok)
            elif tok.startswith("/"):
                diffs.append((current_code, tok[1:]))
                current_code += 1
        return diffs

    # ------------------------------------------------------------------
    # Internal helpers – descriptor
    # ------------------------------------------------------------------

    def _parse_descriptor(self, xref: int, font: PDFFont) -> None:
        try:
            obj = self._doc.xref_object(xref, compressed=False)
        except Exception:
            return

        font.ascent = float(self._get_key(obj, "/Ascent", "0") or 0)
        font.descent = float(self._get_key(obj, "/Descent", "0") or 0)
        font.cap_height = float(self._get_key(obj, "/CapHeight", "0") or 0)
        font.italic_angle = float(self._get_key(obj, "/ItalicAngle", "0") or 0)
        flags = self._get_key(obj, "/Flags", "0")
        font.descriptor_flags = int(flags) if flags.isdigit() else 0

    # ------------------------------------------------------------------
    # Internal helpers – widths
    # ------------------------------------------------------------------

    def _parse_widths(self, obj: str, font: PDFFont) -> None:
        fc = self._get_key(obj, "/FirstChar")
        lc = self._get_key(obj, "/LastChar")
        if not fc or not lc:
            return
        font.first_char = int(fc)
        font.last_char = int(lc)

        # Try to find the widths array – may be a reference or inline.
        m = re.search(r"/Widths\s*\[(.+?)\]", obj, re.DOTALL)
        if m:
            raw = m.group(1).strip()
            if raw:
                font.widths = [float(w) for w in raw.split() if w.replace(".", "").replace("-", "").isdigit()]

    # ------------------------------------------------------------------
    # Internal helpers – embedding
    # ------------------------------------------------------------------

    def _is_embedded(self, font_obj: str, desc_xref: Optional[int]) -> bool:
        if "/FontFile" in font_obj or "/FontFile2" in font_obj or "/FontFile3" in font_obj:
            return True
        if desc_xref:
            try:
                desc_obj = self._doc.xref_object(desc_xref, compressed=False)
                if "/FontFile" in desc_obj or "/FontFile2" in desc_obj or "/FontFile3" in desc_obj:
                    return True
            except Exception:
                pass
        return False

    # ------------------------------------------------------------------
    # Internal helpers – subset detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_subset(base_font: str) -> bool:
        if base_font and len(base_font) > 6:
            prefix = base_font.split("+")[-1] if "+" in base_font else ""
            if "+" in base_font and prefix:
                return True
        return False

    # ------------------------------------------------------------------
    # Internal helpers – stream reading
    # ------------------------------------------------------------------

    def _read_stream(self, xref: int) -> str:
        try:
            raw = self._doc.xref_stream_raw(xref)
            if isinstance(raw, bytes):
                # Try to decompress
                try:
                    import zlib
                    raw = zlib.decompress(raw)
                except Exception:
                    pass
                try:
                    return raw.decode("latin-1")
                except Exception:
                    return raw.decode("utf-8", errors="replace")
            return str(raw)
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Internal helpers – ToUnicode CMap parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_cmap(stream: str) -> Dict[int, str]:
        """Parse a ToUnicode CMap stream and return ``{code: char}``."""
        cmap: Dict[int, str] = {}

        bfchar_blocks = re.findall(
            r"beginbfchar\s*(.*?)\s*endbfchar", stream, re.DOTALL
        )
        for block in bfchar_blocks:
            for line in block.strip().splitlines():
                line = line.strip()
                m = re.match(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", line)
                if m:
                    code = int(m.group(1), 16)
                    hex_str = m.group(2)
                    chars = "".join(
                        chr(int(hex_str[i : i + 4], 16))
                        for i in range(0, len(hex_str), 4)
                    )
                    cmap[code] = chars

        bfrange_blocks = re.findall(
            r"beginbfrange\s*(.*?)\s*endbfrange", stream, re.DOTALL
        )
        for block in bfrange_blocks:
            for line in block.strip().splitlines():
                line = line.strip()
                m = re.match(
                    r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
                    line,
                )
                if m:
                    start = int(m.group(1), 16)
                    end = int(m.group(2), 16)
                    val = int(m.group(3), 16)
                    for i, code in enumerate(range(start, end + 1)):
                        cmap[code] = chr(val + i)

        # Fallback: simple bfchar one-per-line (no block markers)
        if not cmap:
            for m in re.finditer(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", stream):
                code = int(m.group(1), 16)
                hex_str = m.group(2)
                chars = "".join(
                    chr(int(hex_str[i : i + 4], 16))
                    for i in range(0, len(hex_str), 4)
                )
                cmap[code] = chars

        return cmap

    # ------------------------------------------------------------------
    # Internal helpers – family mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _map_family(base_font: str) -> str:
        """Map a PDF base font name to a standard family name."""
        if not base_font:
            return ""
        # Strip subset prefix if present
        clean = base_font.split("+")[-1] if "+" in base_font else base_font
        if clean in _FAMILY_MAP:
            return _FAMILY_MAP[clean]
        # Try prefix matching (e.g. "TimesNewRomanPS-BoldMT" → "Times New Roman")
        for pattern, family in _FAMILY_MAP.items():
            if clean.startswith(pattern):
                return family
        return clean


# ---------------------------------------------------------------------------
# Standalone helper: resolve a fitz Font object to PDFFont
# ---------------------------------------------------------------------------

def font_from_fitz(fitz_font: Any, xref: int = 0) -> PDFFont:
    """Create a :class:`PDFFont` from a fitz ``Font`` object (best-effort)."""
    font = PDFFont(ref=xref)
    try:
        font.name = fitz_font.name or ""
    except AttributeError:
        pass
    try:
        font.base_font = fitz_font.name or ""
    except AttributeError:
        pass
    try:
        font.encoding = fitz_font.encoding or ""
    except AttributeError:
        pass
    try:
        font.embedded = bool(getattr(fitz_font, "is_embedded", False))
    except AttributeError:
        pass
    try:
        font.family = FontHandler._map_family(font.base_font)
    except Exception:
        pass
    return font
