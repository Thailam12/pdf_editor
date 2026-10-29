from dataclasses import dataclass


@dataclass
class TextStyle:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    font_name: str = "Arial"
    font_size: int = 12
    color: str = "#000000"
    alignment: str = "left"

    def to_dict(self):
        return {
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "color": self.color,
            "alignment": self.alignment,
        }

    @staticmethod
    def from_dict(data):
        return TextStyle(**data)


@dataclass
class ParagraphStyle:
    line_spacing: float = 1.0
    space_before: int = 0
    space_after: int = 0
    indent: int = 0

    def to_dict(self):
        return {
            "line_spacing": self.line_spacing,
            "space_before": self.space_before,
            "space_after": self.space_after,
            "indent": self.indent,
        }


class FormattingManager:
    def __init__(self):
        self.current_style = TextStyle()
        self.current_paragraph_style = ParagraphStyle()

    @property
    def text_style(self):
        """Alias for :attr:`current_style` (used by the editor UI)."""
        return self.current_style

    def set_bold(self, value):
        self.current_style.bold = value

    def set_italic(self, value):
        self.current_style.italic = value

    def set_underline(self, value):
        self.current_style.underline = value

    def toggle_bold(self):
        self.current_style.bold = not self.current_style.bold

    def toggle_italic(self):
        self.current_style.italic = not self.current_style.italic

    def toggle_underline(self):
        self.current_style.underline = not self.current_style.underline

    def set_font(self, font_name):
        self.current_style.font_name = font_name

    def set_font_name(self, font_name):
        """Alias for :meth:`set_font` (used by the editor UI)."""
        self.set_font(font_name)

    def set_font_size(self, size):
        self.current_style.font_size = size

    def set_color(self, color):
        self.current_style.color = color

    def set_alignment(self, alignment):
        self.current_style.alignment = alignment

    def get_font_spec(self):
        style = ""
        if self.current_style.bold:
            style += "bold "
        if self.current_style.italic:
            style += "italic"
        return (self.current_style.font_name, self.current_style.font_size, style.strip())
