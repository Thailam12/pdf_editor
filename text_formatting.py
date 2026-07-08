# text_formatting.py - Text formatting styles
from dataclasses import dataclass
from typing import Optional

@dataclass
class TextStyle:
    """Represents text formatting style"""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    font_name: str = "Arial"
    font_size: int = 12
    color: str = "#000000"
    alignment: str = "left"  # left, center, right, justify
    
    def to_dict(self):
        return {
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "color": self.color,
            "alignment": self.alignment
        }
    
    @staticmethod
    def from_dict(data):
        return TextStyle(**data)

@dataclass
class ParagraphStyle:
    """Represents paragraph formatting"""
    line_spacing: float = 1.0
    space_before: int = 0
    space_after: int = 0
    indent: int = 0
    
    def to_dict(self):
        return {
            "line_spacing": self.line_spacing,
            "space_before": self.space_before,
            "space_after": self.space_after,
            "indent": self.indent
        }

class FormattingManager:
    """Manages text and paragraph formatting"""
    def __init__(self):
        self.current_style = TextStyle()
        self.current_paragraph_style = ParagraphStyle()
    
    def set_bold(self, value):
        self.current_style.bold = value
    
    def set_italic(self, value):
        self.current_style.italic = value
    
    def set_underline(self, value):
        self.current_style.underline = value
    
    def set_font(self, font_name):
        self.current_style.font_name = font_name
    
    def set_font_size(self, size):
        self.current_style.font_size = size
    
    def set_color(self, color):
        self.current_style.color = color
    
    def set_alignment(self, alignment):
        self.current_style.alignment = alignment
    
    def get_font_spec(self):
        """Get font specification for Tkinter"""
        style = ""
        if self.current_style.bold:
            style += "bold "
        if self.current_style.italic:
            style += "italic"
        
        return (self.current_style.font_name, self.current_style.font_size, style.strip())
