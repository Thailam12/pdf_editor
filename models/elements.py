import math
import base64
from copy import deepcopy


class BaseElement:
    type_name = ""

    def __init__(self, page=0):
        self.page = page
        self.locked = False
        self.visible = True
        self.opacity = 1.0
        self.name = ""

    def get_bounds(self):
        raise NotImplementedError

    def contains_point(self, x, y):
        bx, by, bw, bh = self.get_bounds()
        return bx - 5 <= x <= bx + bw + 5 and by - 5 <= y <= by + bh + 5

    def to_tuple(self):
        raise NotImplementedError

    def to_json(self):
        etype, params = self.to_tuple()
        params["page"] = self.page
        params["locked"] = self.locked
        params["visible"] = self.visible
        params["opacity"] = self.opacity
        params["name"] = self.name
        return {"type": etype, "params": params}

    def __deepcopy__(self, memo):
        cls = type(self)
        obj = cls.__new__(cls)
        obj.__dict__.update(deepcopy(self.__dict__, memo))
        return obj

    def __copy__(self):
        cls = type(self)
        obj = cls.__new__(cls)
        obj.__dict__.update(self.__dict__.copy())
        return obj


class TextElement(BaseElement):
    type_name = "text"

    def __init__(self, text="", x=0, y=0, size=12, font_name="Arial",
                 color="#000000", bold=False, italic=False, underline=False,
                 alignment="left", page=0):
        super().__init__(page)
        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.font_name = font_name
        self.color = color
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.alignment = alignment

    def get_bounds(self):
        text_len = len(self.text)
        w = max(100, text_len * (self.size * 0.6))
        h = self.size * 2
        return (self.x, self.y, w, h)

    def to_tuple(self):
        return ("text", {
            "text": self.text, "x": self.x, "y": self.y,
            "size": self.size, "font_name": self.font_name,
            "color": self.color, "bold": self.bold,
            "italic": self.italic, "underline": self.underline,
            "alignment": self.alignment,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            text=params.get("text", ""),
            x=params.get("x", 0), y=params.get("y", 0),
            size=params.get("size", 12),
            font_name=params.get("font_name", "Arial"),
            color=params.get("color", "#000000"),
            bold=params.get("bold", False),
            italic=params.get("italic", False),
            underline=params.get("underline", False),
            alignment=params.get("alignment", "left"),
            page=params.get("page", 0),
        )


class ImageElement(BaseElement):
    type_name = "image"

    def __init__(self, path="", x=0, y=0, w=100, h=100, page=0):
        super().__init__(page)
        self.path = path
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("image", {
            "path": self.path, "x": self.x, "y": self.y,
            "w": self.w, "h": self.h,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            path=params.get("path", ""),
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 100), h=params.get("h", 100),
            page=params.get("page", 0),
        )


class ShapeElement(BaseElement):
    type_name = "shape"

    def __init__(self, shape_type="rect", x=0, y=0, w=100, h=100,
                 color="red", filled=False, fill_color="", page=0,
                 stroke_width=2):
        super().__init__(page)
        self.shape_type = shape_type
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.color = color
        self.filled = filled
        self.fill_color = fill_color or color
        self.stroke_width = stroke_width

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return (self.shape_type, {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "color": self.color, "filled": self.filled,
            "fill_color": self.fill_color, "stroke_width": self.stroke_width,
        })

    @classmethod
    def from_params(cls, etype, params):
        return cls(
            shape_type=etype,
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 100), h=params.get("h", 100),
            color=params.get("color", "red"),
            filled=params.get("filled", False),
            fill_color=params.get("fill_color", ""),
            stroke_width=params.get("stroke_width", 2),
            page=params.get("page", 0),
        )


class LineElement(BaseElement):
    type_name = "line"

    def __init__(self, x1=0, y1=0, x2=100, y2=100, color="red", width=2, page=0):
        super().__init__(page)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color
        self.width = width

    def get_bounds(self):
        x = min(self.x1, self.x2)
        y = min(self.y1, self.y2)
        w = abs(self.x2 - self.x1) or 5
        h = abs(self.y2 - self.y1) or 5
        return (x, y, w, h)

    def contains_point(self, x, y):
        bx, by, bw, bh = self.get_bounds()
        if x < bx - 5 or x > bx + bw + 5 or y < by - 5 or y > by + bh + 5:
            return False
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        if dx == 0 and dy == 0:
            return abs(x - self.x1) < 8 and abs(y - self.y1) < 8
        t = ((x - self.x1) * dx + (y - self.y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        cx = self.x1 + t * dx
        cy = self.y1 + t * dy
        dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        return dist < 10

    def to_tuple(self):
        return ("line", {
            "x1": self.x1, "y1": self.y1,
            "x2": self.x2, "y2": self.y2,
            "color": self.color, "width": self.width,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x1=params.get("x1", 0), y1=params.get("y1", 0),
            x2=params.get("x2", 100), y2=params.get("y2", 100),
            color=params.get("color", "red"),
            width=params.get("width", 2),
            page=params.get("page", 0),
        )


class HighlightElement(BaseElement):
    type_name = "highlight"

    def __init__(self, x=0, y=0, w=200, h=20, color="#FFFF00",
                 opacity=0.4, page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.color = color
        self.opacity = opacity

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("highlight", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "color": self.color, "opacity": self.opacity,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 200), h=params.get("h", 20),
            color=params.get("color", "#FFFF00"),
            opacity=params.get("opacity", 0.4),
            page=params.get("page", 0),
        )


class AnnotationElement(BaseElement):
    type_name = "annotation"

    def __init__(self, x=0, y=0, w=200, h=16, style="underline",
                 color="#FF0000", opacity=1.0, stroke_width=2, page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.style = style
        self.color = color
        self.opacity = opacity
        self.stroke_width = stroke_width

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("annotation", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "style": self.style, "color": self.color,
            "opacity": self.opacity, "stroke_width": self.stroke_width,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 200), h=params.get("h", 16),
            style=params.get("style", "underline"),
            color=params.get("color", "#FF0000"),
            opacity=params.get("opacity", 1.0),
            stroke_width=params.get("stroke_width", 2),
            page=params.get("page", 0),
        )


class NoteElement(BaseElement):
    type_name = "note"

    def __init__(self, x=0, y=0, text="", color="#FFA500",
                 author="User", page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.author = author
        self.size = 28

    def get_bounds(self):
        return (self.x, self.y, self.size, self.size)

    def to_tuple(self):
        return ("note", {
            "x": self.x, "y": self.y, "text": self.text,
            "color": self.color, "author": self.author,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            text=params.get("text", ""),
            color=params.get("color", "#FFA500"),
            author=params.get("author", "User"),
            page=params.get("page", 0),
        )


class StampElement(BaseElement):
    type_name = "stamp"

    def __init__(self, x=0, y=0, w=150, h=50, text="APPROVED",
                 color="#FF0000", rotation=0, opacity=0.8,
                 font_size=24, font_name="Arial", bold=True, page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.color = color
        self.rotation = rotation
        self.opacity = opacity
        self.font_size = font_size
        self.font_name = font_name
        self.bold = bold

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("stamp", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "text": self.text, "color": self.color,
            "rotation": self.rotation, "opacity": self.opacity,
            "font_size": self.font_size, "font_name": self.font_name,
            "bold": self.bold,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 150), h=params.get("h", 50),
            text=params.get("text", "APPROVED"),
            color=params.get("color", "#FF0000"),
            rotation=params.get("rotation", 0),
            opacity=params.get("opacity", 0.8),
            font_size=params.get("font_size", 24),
            font_name=params.get("font_name", "Arial"),
            bold=params.get("bold", True),
            page=params.get("page", 0),
        )


class SignatureElement(BaseElement):
    type_name = "signature"

    def __init__(self, x=0, y=0, w=200, h=60, text="",
                 image_data="", color="#000066", page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.image_data = image_data
        self.color = color

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("signature", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "text": self.text, "image_data": self.image_data,
            "color": self.color,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 200), h=params.get("h", 60),
            text=params.get("text", ""),
            image_data=params.get("image_data", ""),
            color=params.get("color", "#000066"),
            page=params.get("page", 0),
        )


class FreehandElement(BaseElement):
    type_name = "freehand"

    def __init__(self, points=None, color="#FF0000", width=2, page=0):
        super().__init__(page)
        self.points = points or []
        self.color = color
        self.width = width

    def get_bounds(self):
        if not self.points:
            return (0, 0, 10, 10)
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (min(xs), min(ys), max(xs) - min(xs) or 5, max(ys) - min(ys) or 5)

    def contains_point(self, x, y):
        if not self.points:
            return False
        bx, by, bw, bh = self.get_bounds()
        if x < bx - 10 or x > bx + bw + 10 or y < by - 10 or y > by + bh + 10:
            return False
        for px, py in self.points:
            if abs(x - px) < 8 and abs(y - py) < 8:
                return True
        return False

    def to_tuple(self):
        return ("freehand", {
            "points": self.points, "color": self.color,
            "width": self.width,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            points=params.get("points", []),
            color=params.get("color", "#FF0000"),
            width=params.get("width", 2),
            page=params.get("page", 0),
        )


class LinkElement(BaseElement):
    type_name = "link"

    def __init__(self, x=0, y=0, w=100, h=20, url="",
                 text="", color="#0066CC", page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.url = url
        self.text = text
        self.color = color

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("link", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "url": self.url, "text": self.text, "color": self.color,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 100), h=params.get("h", 20),
            url=params.get("url", ""),
            text=params.get("text", ""),
            color=params.get("color", "#0066CC"),
            page=params.get("page", 0),
        )


class RedactElement(BaseElement):
    type_name = "redact"

    def __init__(self, x=0, y=0, w=100, h=20, color="#000000",
                 label="", page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.color = color
        self.label = label

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("redact", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "color": self.color, "label": self.label,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 100), h=params.get("h", 20),
            color=params.get("color", "#000000"),
            label=params.get("label", ""),
            page=params.get("page", 0),
        )


class WatermarkElement(BaseElement):
    type_name = "watermark"

    def __init__(self, text="WATERMARK", x=0, y=0, size=60,
                 color="#888888", opacity=0.3, rotation=45,
                 font_name="Arial", page=0):
        super().__init__(page)
        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.opacity = opacity
        self.rotation = rotation
        self.font_name = font_name

    def get_bounds(self):
        return (self.x, self.y, self.size * len(self.text) * 0.6, self.size * 2)

    def to_tuple(self):
        return ("watermark", {
            "text": self.text, "x": self.x, "y": self.y,
            "size": self.size, "color": self.color,
            "opacity": self.opacity, "rotation": self.rotation,
            "font_name": self.font_name,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            text=params.get("text", "WATERMARK"),
            x=params.get("x", 0), y=params.get("y", 0),
            size=params.get("size", 60),
            color=params.get("color", "#888888"),
            opacity=params.get("opacity", 0.3),
            rotation=params.get("rotation", 45),
            font_name=params.get("font_name", "Arial"),
            page=params.get("page", 0),
        )


class FormFieldElement(BaseElement):
    type_name = "formfield"

    def __init__(self, x=0, y=0, w=200, h=24, field_type="text",
                 field_name="", value="", font_size=12,
                 color="#000000", required=False, page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.field_type = field_type
        self.field_name = field_name
        self.value = value
        self.font_size = font_size
        self.color = color
        self.required = required

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("formfield", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "field_type": self.field_type, "field_name": self.field_name,
            "value": self.value, "font_size": self.font_size,
            "color": self.color, "required": self.required,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 200), h=params.get("h", 24),
            field_type=params.get("field_type", "text"),
            field_name=params.get("field_name", ""),
            value=params.get("value", ""),
            font_size=params.get("font_size", 12),
            color=params.get("color", "#000000"),
            required=params.get("required", False),
            page=params.get("page", 0),
        )


class HeaderFooterElement(BaseElement):
    type_name = "headerfooter"

    def __init__(self, text="{page} / {total}", x=0, y=0,
                 size=10, color="#666666", font_name="Arial",
                 position="footer-center", page=-1):
        super().__init__(page)
        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.font_name = font_name
        self.position = position

    def get_bounds(self):
        return (self.x, self.y, 300, self.size * 2)

    def to_tuple(self):
        return ("headerfooter", {
            "text": self.text, "x": self.x, "y": self.y,
            "size": self.size, "color": self.color,
            "font_name": self.font_name, "position": self.position,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            text=params.get("text", "{page} / {total}"),
            x=params.get("x", 0), y=params.get("y", 0),
            size=params.get("size", 10),
            color=params.get("color", "#666666"),
            font_name=params.get("font_name", "Arial"),
            position=params.get("position", "footer-center"),
            page=params.get("page", -1),
        )


class AttachmentElement(BaseElement):
    type_name = "attachment"

    def __init__(self, file_path="", name="", description="",
                 page=0):
        super().__init__(page)
        self.file_path = file_path
        self.name = name or file_path
        self.description = description

    def get_bounds(self):
        return (0, 0, 30, 30)

    def to_tuple(self):
        return ("attachment", {
            "file_path": self.file_path, "name": self.name,
            "description": self.description,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            file_path=params.get("file_path", ""),
            name=params.get("name", ""),
            description=params.get("description", ""),
            page=params.get("page", 0),
        )


class MeasurementElement(BaseElement):
    type_name = "measurement"

    def __init__(self, x1=0, y1=0, x2=100, y2=0, measurement_type="distance",
                 points_list=None, unit="mm", scale=1.0, color="#FF0000",
                 width=2, font_size=10, show_label=True, page=0):
        super().__init__(page)
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.measurement_type = measurement_type
        self.points_list = points_list or []
        self.unit = unit
        self.scale = scale
        self.color = color
        self.width = width
        self.font_size = font_size
        self.show_label = show_label

    def _get_pixel_length(self):
        if self.measurement_type == "line" or self.measurement_type == "distance":
            return math.sqrt((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2)
        if self.points_list and len(self.points_list) >= 2:
            total = 0
            for i in range(len(self.points_list) - 1):
                dx = self.points_list[i + 1][0] - self.points_list[i][0]
                dy = self.points_list[i + 1][1] - self.points_list[i][1]
                total += math.sqrt(dx * dx + dy * dy)
            return total
        return 0.0

    def get_length(self):
        return self._get_pixel_length() / self.scale if self.scale else 0.0

    def get_perimeter(self):
        if self.points_list and len(self.points_list) >= 2:
            total = 0
            for i in range(len(self.points_list) - 1):
                dx = self.points_list[i + 1][0] - self.points_list[i][0]
                dy = self.points_list[i + 1][1] - self.points_list[i][1]
                total += math.sqrt(dx * dx + dy * dy)
            if len(self.points_list) > 2:
                dx = self.points_list[0][0] - self.points_list[-1][0]
                dy = self.points_list[0][1] - self.points_list[-1][1]
                total += math.sqrt(dx * dx + dy * dy)
            return total / self.scale if self.scale else 0.0
        return self.get_length()

    def get_area(self):
        if self.points_list and len(self.points_list) >= 3:
            area = 0.0
            n = len(self.points_list)
            for i in range(n):
                j = (i + 1) % n
                area += self.points_list[i][0] * self.points_list[j][1]
                area -= self.points_list[j][0] * self.points_list[i][1]
            return abs(area) / (2.0 * self.scale * self.scale) if self.scale else 0.0
        return 0.0

    def get_bounds(self):
        if self.measurement_type in ("perimeter", "area") and self.points_list:
            xs = [p[0] for p in self.points_list]
            ys = [p[1] for p in self.points_list]
            return (min(xs), min(ys), max(xs) - min(xs) or 5, max(ys) - min(ys) or 5)
        x = min(self.x1, self.x2)
        y = min(self.y1, self.y2)
        w = abs(self.x2 - self.x1) or 5
        h = abs(self.y2 - self.y1) or 5
        return (x, y, w, h)

    def contains_point(self, x, y):
        bx, by, bw, bh = self.get_bounds()
        if x < bx - 10 or x > bx + bw + 10 or y < by - 10 or y > by + bh + 10:
            return False
        if self.measurement_type in ("perimeter", "area") and self.points_list:
            for px, py in self.points_list:
                if abs(x - px) < 8 and abs(y - py) < 8:
                    return True
            return False
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        if dx == 0 and dy == 0:
            return abs(x - self.x1) < 8 and abs(y - self.y1) < 8
        t = ((x - self.x1) * dx + (y - self.y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        cx = self.x1 + t * dx
        cy = self.y1 + t * dy
        dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        return dist < 10

    def to_tuple(self):
        return ("measurement", {
            "x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2,
            "measurement_type": self.measurement_type,
            "points_list": self.points_list, "unit": self.unit,
            "scale": self.scale, "color": self.color, "width": self.width,
            "font_size": self.font_size, "show_label": self.show_label,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x1=params.get("x1", 0), y1=params.get("y1", 0),
            x2=params.get("x2", 100), y2=params.get("y2", 0),
            measurement_type=params.get("measurement_type", "distance"),
            points_list=params.get("points_list", []),
            unit=params.get("unit", "mm"),
            scale=params.get("scale", 1.0),
            color=params.get("color", "#FF0000"),
            width=params.get("width", 2),
            font_size=params.get("font_size", 10),
            show_label=params.get("show_label", True),
            page=params.get("page", 0),
        )


class CalloutElement(BaseElement):
    type_name = "callout"

    def __init__(self, x=0, y=0, w=150, h=80, text="",
                 tail_x=0, tail_y=0, color="#000000",
                 font_size=12, font_name="Arial",
                 fill_color="#FFFFCC", border_color="#000000",
                 border_width=1, text_color="#000000", page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.tail_x = tail_x
        self.tail_y = tail_y
        self.color = color
        self.font_size = font_size
        self.font_name = font_name
        self.fill_color = fill_color
        self.border_color = border_color
        self.border_width = border_width
        self.text_color = text_color

    def get_bounds(self):
        min_x = min(self.x, self.tail_x)
        min_y = min(self.y, self.tail_y)
        max_x = max(self.x + self.w, self.tail_x)
        max_y = max(self.y + self.h, self.tail_y)
        return (min_x, min_y, max_x - min_x or 5, max_y - min_y or 5)

    def to_tuple(self):
        return ("callout", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "text": self.text, "tail_x": self.tail_x, "tail_y": self.tail_y,
            "color": self.color, "font_size": self.font_size,
            "font_name": self.font_name, "fill_color": self.fill_color,
            "border_color": self.border_color, "border_width": self.border_width,
            "text_color": self.text_color,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 150), h=params.get("h", 80),
            text=params.get("text", ""),
            tail_x=params.get("tail_x", 0), tail_y=params.get("tail_y", 0),
            color=params.get("color", "#000000"),
            font_size=params.get("font_size", 12),
            font_name=params.get("font_name", "Arial"),
            fill_color=params.get("fill_color", "#FFFFCC"),
            border_color=params.get("border_color", "#000000"),
            border_width=params.get("border_width", 1),
            text_color=params.get("text_color", "#000000"),
            page=params.get("page", 0),
        )


class TextBoxElement(BaseElement):
    type_name = "textbox"

    def __init__(self, x=0, y=0, w=200, h=100, text="",
                 font_size=12, font_name="Arial", color="#000000",
                 fill_color="", border_color="#000000", border_width=1,
                 alignment="left", padding=4, word_wrap=True, page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.font_size = font_size
        self.font_name = font_name
        self.color = color
        self.fill_color = fill_color
        self.border_color = border_color
        self.border_width = border_width
        self.alignment = alignment
        self.padding = padding
        self.word_wrap = word_wrap

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("textbox", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "text": self.text, "font_size": self.font_size,
            "font_name": self.font_name, "color": self.color,
            "fill_color": self.fill_color, "border_color": self.border_color,
            "border_width": self.border_width, "alignment": self.alignment,
            "padding": self.padding, "word_wrap": self.word_wrap,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 200), h=params.get("h", 100),
            text=params.get("text", ""),
            font_size=params.get("font_size", 12),
            font_name=params.get("font_name", "Arial"),
            color=params.get("color", "#000000"),
            fill_color=params.get("fill_color", ""),
            border_color=params.get("border_color", "#000000"),
            border_width=params.get("border_width", 1),
            alignment=params.get("alignment", "left"),
            padding=params.get("padding", 4),
            word_wrap=params.get("word_wrap", True),
            page=params.get("page", 0),
        )


class VideoElement(BaseElement):
    type_name = "video"

    def __init__(self, x=0, y=0, w=320, h=240, file_path="",
                 poster_image_path=None, duration=0, page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.file_path = file_path
        self.poster_image_path = poster_image_path
        self.duration = duration

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("video", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "file_path": self.file_path,
            "poster_image_path": self.poster_image_path,
            "duration": self.duration,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 320), h=params.get("h", 240),
            file_path=params.get("file_path", ""),
            poster_image_path=params.get("poster_image_path", None),
            duration=params.get("duration", 0),
            page=params.get("page", 0),
        )


class AudioElement(BaseElement):
    type_name = "audio"

    def __init__(self, x=0, y=0, file_path="", duration=0, page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.file_path = file_path
        self.duration = duration

    def get_bounds(self):
        return (self.x, self.y, 200, 40)

    def to_tuple(self):
        return ("audio", {
            "x": self.x, "y": self.y,
            "file_path": self.file_path, "duration": self.duration,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            file_path=params.get("file_path", ""),
            duration=params.get("duration", 0),
            page=params.get("page", 0),
        )


class BarcodeElement(BaseElement):
    type_name = "barcode"

    def __init__(self, x=0, y=0, w=200, h=100, data="",
                 barcode_type="qr", color="#000000",
                 background_color="#FFFFFF", show_text=True,
                 font_size=8, page=0):
        super().__init__(page)
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.data = data
        self.barcode_type = barcode_type
        self.color = color
        self.background_color = background_color
        self.show_text = show_text
        self.font_size = font_size

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return ("barcode", {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "data": self.data, "barcode_type": self.barcode_type,
            "color": self.color, "background_color": self.background_color,
            "show_text": self.show_text, "font_size": self.font_size,
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x=params.get("x", 0), y=params.get("y", 0),
            w=params.get("w", 200), h=params.get("h", 100),
            data=params.get("data", ""),
            barcode_type=params.get("barcode_type", "qr"),
            color=params.get("color", "#000000"),
            background_color=params.get("background_color", "#FFFFFF"),
            show_text=params.get("show_text", True),
            font_size=params.get("font_size", 8),
            page=params.get("page", 0),
        )


_ELEMENT_TYPE_MAP = {
    "text": TextElement,
    "image": ImageElement,
    "line": LineElement,
    "rect": ShapeElement,
    "ellipse": ShapeElement,
    "triangle": ShapeElement,
    "highlight": HighlightElement,
    "annotation": AnnotationElement,
    "note": NoteElement,
    "stamp": StampElement,
    "signature": SignatureElement,
    "freehand": FreehandElement,
    "link": LinkElement,
    "redact": RedactElement,
    "watermark": WatermarkElement,
    "formfield": FormFieldElement,
    "headerfooter": HeaderFooterElement,
    "attachment": AttachmentElement,
    "measurement": MeasurementElement,
    "callout": CalloutElement,
    "textbox": TextBoxElement,
    "video": VideoElement,
    "audio": AudioElement,
    "barcode": BarcodeElement,
}

PREDEFINED_STAMPS = [
    {"text": "APPROVED", "color": "#00AA00", "icon": "✓"},
    {"text": "REJECTED", "color": "#CC0000", "icon": "✗"},
    {"text": "DRAFT", "color": "#FF8800", "icon": "D"},
    {"text": "CONFIDENTIAL", "color": "#CC0000", "icon": "C"},
    {"text": "FINAL", "color": "#0066CC", "icon": "F"},
    {"text": "NOT APPROVED", "color": "#CC0000", "icon": "N"},
    {"text": "REVIEWED", "color": "#008800", "icon": "R"},
    {"text": "PENDING", "color": "#FF8800", "icon": "P"},
    {"text": "VOID", "color": "#CC0000", "icon": "V"},
    {"text": "COPY", "color": "#888888", "icon": "©"},
    {"text": "ORIGINAL", "color": "#000000", "icon": "O"},
    {"text": "PAID", "color": "#00AA00", "icon": "$"},
]


def element_from_json(data):
    if not isinstance(data, dict):
        return None
    etype = data.get("type", "")
    params = data.get("params", {})
    klass = _ELEMENT_TYPE_MAP.get(etype)
    if klass is None:
        return None
    if klass is TextElement:
        return TextElement.from_params(params)
    if klass is ImageElement:
        return ImageElement.from_params(params)
    if klass is LineElement:
        return LineElement.from_params(params)
    if klass is ShapeElement:
        return ShapeElement.from_params(etype, params)
    if klass is HighlightElement:
        return HighlightElement.from_params(params)
    if klass is AnnotationElement:
        return AnnotationElement.from_params(params)
    if klass is NoteElement:
        return NoteElement.from_params(params)
    if klass is StampElement:
        return StampElement.from_params(params)
    if klass is SignatureElement:
        return SignatureElement.from_params(params)
    if klass is FreehandElement:
        return FreehandElement.from_params(params)
    if klass is LinkElement:
        return LinkElement.from_params(params)
    if klass is RedactElement:
        return RedactElement.from_params(params)
    if klass is WatermarkElement:
        return WatermarkElement.from_params(params)
    if klass is FormFieldElement:
        return FormFieldElement.from_params(params)
    if klass is HeaderFooterElement:
        return HeaderFooterElement.from_params(params)
    if klass is AttachmentElement:
        return AttachmentElement.from_params(params)
    if klass is MeasurementElement:
        return MeasurementElement.from_params(params)
    if klass is CalloutElement:
        return CalloutElement.from_params(params)
    if klass is TextBoxElement:
        return TextBoxElement.from_params(params)
    if klass is VideoElement:
        return VideoElement.from_params(params)
    if klass is AudioElement:
        return AudioElement.from_params(params)
    if klass is BarcodeElement:
        return BarcodeElement.from_params(params)
    return None


def elements_from_json_list(data_list):
    if not isinstance(data_list, list):
        return []
    result = []
    for item in data_list:
        obj = element_from_json(item)
        if obj is not None:
            result.append(obj)
    return result


def elements_to_json_list(elements):
    return [e.to_json() for e in elements if hasattr(e, "to_json")]


def elements_from_tuples(tuples_list):
    result = []
    for item in tuples_list:
        if isinstance(item, tuple) and len(item) == 2:
            etype, params = item
            obj = element_from_json({"type": etype, "params": params})
            if obj is not None:
                result.append(obj)
    return result
