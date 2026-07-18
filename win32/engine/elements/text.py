"""Text element models for the PDF editor.

Supports three text paradigms: editing existing PDF text inline,
adding new rich-text blocks, and automatic/template-driven text.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from engine.elements.base import BaseElement


@dataclass
class TextRun:
    """A single styled span of text within a TextElement."""

    text: str = ""
    font_name: str = "Helvetica"
    font_size: float = 12.0
    color: Tuple[float, float, float, float] = (0, 0, 0, 1.0)
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False

    @property
    def effective_font(self) -> str:
        base = self.font_name
        if self.bold and "Bold" not in base:
            base = f"{base}-Bold"
        if self.italic and "Italic" not in base:
            base = f"{base}-Italic"
        return base

    def estimate_width(self, char_width: float = 6.0) -> float:
        return len(self.text) * self.font_size * 0.6 * (char_width / 6.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "color": list(self.color),
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "strikethrough": self.strikethrough,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TextRun:
        return cls(
            text=data.get("text", ""),
            font_name=data.get("font_name", "Helvetica"),
            font_size=data.get("font_size", 12.0),
            color=tuple(data.get("color", [0, 0, 0, 1.0])),
            bold=data.get("bold", False),
            italic=data.get("italic", False),
            underline=data.get("underline", False),
            strikethrough=data.get("strikethrough", False),
        )


@dataclass
class InlineTextEdit:
    """Describes an edit to text that already exists on a PDF page.

    Tracks the original position and font so the editor can perform
    seamless in-place replacement without disturbing surrounding glyphs.
    """

    original_text: str = ""
    replacement_text: str = ""
    font_name: str = "Helvetica"
    font_size: float = 12.0
    color: Tuple[float, float, float] = (0, 0, 0)
    position: Tuple[float, float] = (0, 0)
    line_height: float = 14.0
    word_wrap_width: float = 0.0

    @property
    def is_multiline(self) -> bool:
        return "\n" in self.replacement_text

    @property
    def delta_length(self) -> int:
        return len(self.replacement_text) - len(self.original_text)

    def wrap_text(self, max_width: float) -> List[str]:
        if max_width <= 0:
            return [self.replacement_text]
        avg_char = self.font_size * 0.6
        if avg_char <= 0:
            return [self.replacement_text]
        chars_per_line = max(1, int(max_width / avg_char))
        words = self.replacement_text.split()
        lines: List[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip() if current else word
            if len(test) * avg_char <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "replacement_text": self.replacement_text,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "color": list(self.color),
            "position": list(self.position),
            "line_height": self.line_height,
            "word_wrap_width": self.word_wrap_width,
        }


class TextElement(BaseElement):
    """Rich text block composed of multiple styled runs."""

    def __init__(
        self,
        page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        runs: Optional[List[TextRun]] = None,
        alignment: str = "left",
        line_spacing: float = 1.2,
        word_wrap_width: float = 0.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kwargs)
        self.runs: List[TextRun] = runs or []
        self.alignment = alignment
        self.line_spacing = line_spacing
        self.word_wrap_width = word_wrap_width

    @property
    def plain_text(self) -> str:
        return "".join(r.text for r in self.runs)

    def add_run(self, run: TextRun) -> None:
        self.runs.append(run)

    def set_text(self, text: str, font_name: str = "Helvetica",
                 font_size: float = 12.0,
                 color: Tuple[float, float, float, float] = (0, 0, 0, 1.0)) -> None:
        self.runs = [TextRun(text=text, font_name=font_name,
                             font_size=font_size, color=color)]

    def split_run_at(self, index: int, position: int) -> None:
        """Split a run at the given character index into two runs."""
        if index >= len(self.runs):
            return
        run = self.runs[index]
        pos = max(0, min(position, len(run.text)))
        left = TextRun(text=run.text[:pos], font_name=run.font_name,
                       font_size=run.font_size, color=run.color,
                       bold=run.bold, italic=run.italic,
                       underline=run.underline, strikethrough=run.strikethrough)
        right = TextRun(text=run.text[pos:], font_name=run.font_name,
                        font_size=run.font_size, color=run.color,
                        bold=run.bold, italic=run.italic,
                        underline=run.underline, strikethrough=run.strikethrough)
        self.runs[index: index + 1] = [left, right]

    def word_wrap(self, max_width: float) -> List[TextRun]:
        if max_width <= 0 or not self.runs:
            return list(self.runs)
        result: List[TextRun] = []
        current_line_width = 0.0
        for run in self.runs:
            words = run.text.split(" ")
            for i, word in enumerate(words):
                word_w = len(word) * run.font_size * 0.6
                space_w = run.font_size * 0.3
                if current_line_width + word_w > max_width and current_line_width > 0:
                    result.append(TextRun(
                        text="\n", font_name=run.font_name,
                        font_size=run.font_size, color=run.color,
                    ))
                    current_line_width = 0.0
                prefix = " " if i > 0 and current_line_width > 0 else ""
                result.append(TextRun(
                    text=f"{prefix}{word}", font_name=run.font_name,
                    font_size=run.font_size, color=run.color,
                    bold=run.bold, italic=run.italic,
                    underline=run.underline, strikethrough=run.strikethrough,
                ))
                current_line_width += len(prefix + word) * run.font_size * 0.6 + space_w
        self.runs = result
        return result

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "TextElement",
            "runs": [r.to_dict() for r in self.runs],
            "alignment": self.alignment,
            "line_spacing": self.line_spacing,
            "word_wrap_width": self.word_wrap_width,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TextElement:
        runs = [TextRun.from_dict(r) for r in data.get("runs", [])]
        elem = cls(
            page=data["page"],
            bbox=tuple(data["bbox"]),
            runs=runs,
            alignment=data.get("alignment", "left"),
            line_spacing=data.get("line_spacing", 1.2),
            word_wrap_width=data.get("word_wrap_width", 0.0),
            locked=data.get("locked", False),
            visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0),
            name=data.get("name", ""),
            layer=data.get("layer", ""),
            z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> TextElement:
        import copy
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new


class AutoTextElement(BaseElement):
    """Template-based text that is resolved at render time.

    Supports placeholders: ``{page_number}``, ``{total_pages}``,
    ``{date}``, ``{filename}``, ``{custom_<key>}``.
    """

    _PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

    def __init__(
        self,
        page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        template: str = "",
        font_name: str = "Helvetica",
        font_size: float = 10.0,
        color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        alignment: str = "center",
        custom_vars: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kwargs)
        self.template = template
        self.font_name = font_name
        self.font_size = font_size
        self.color = color
        self.alignment = alignment
        self.custom_vars: Dict[str, str] = custom_vars or {}

    @property
    def available_placeholders(self) -> List[str]:
        return self._PLACEHOLDER_RE.findall(self.template)

    def resolve(
        self,
        page_number: int = 1,
        total_pages: int = 1,
        filename: str = "",
        date: str = "",
    ) -> str:
        mapping: Dict[str, str] = {
            "page_number": str(page_number),
            "total_pages": str(total_pages),
            "filename": filename,
            "date": date,
        }
        mapping.update(self.custom_vars)

        def _replace(m: re.Match) -> str:
            key = m.group(1)
            return mapping.get(key, m.group(0))

        return self._PLACEHOLDER_RE.sub(_replace, self.template)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "AutoTextElement",
            "template": self.template,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "color": list(self.color),
            "alignment": self.alignment,
            "custom_vars": self.custom_vars,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AutoTextElement:
        elem = cls(
            page=data["page"],
            bbox=tuple(data["bbox"]),
            template=data.get("template", ""),
            font_name=data.get("font_name", "Helvetica"),
            font_size=data.get("font_size", 10.0),
            color=tuple(data.get("color", [0, 0, 0, 1.0])),
            alignment=data.get("alignment", "center"),
            custom_vars=data.get("custom_vars", {}),
            locked=data.get("locked", False),
            visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0),
            name=data.get("name", ""),
            layer=data.get("layer", ""),
            z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> AutoTextElement:
        import copy
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new
