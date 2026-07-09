import math
from copy import deepcopy


class BaseElement:
    type_name = ""

    def __init__(self, page=0):
        self.page = page

    def get_bounds(self):
        raise NotImplementedError

    def contains_point(self, x, y):
        bx, by, bw, bh = self.get_bounds()
        return bx - 5 <= x <= bx + bw + 5 and by - 5 <= y <= by + bh + 5

    def to_tuple(self):
        raise NotImplementedError

    def to_json(self):
        etype, params = self.to_tuple()
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
            "alignment": self.alignment, "page": self.page
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            text=params.get("text", ""),
            x=params.get("x", 0),
            y=params.get("y", 0),
            size=params.get("size", 12),
            font_name=params.get("font_name", "Arial"),
            color=params.get("color", "#000000"),
            bold=params.get("bold", False),
            italic=params.get("italic", False),
            underline=params.get("underline", False),
            alignment=params.get("alignment", "left"),
            page=params.get("page", 0)
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
            "w": self.w, "h": self.h, "page": self.page
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            path=params.get("path", ""),
            x=params.get("x", 0),
            y=params.get("y", 0),
            w=params.get("w", 100),
            h=params.get("h", 100),
            page=params.get("page", 0)
        )


class ShapeElement(BaseElement):
    type_name = "shape"

    def __init__(self, shape_type="rect", x=0, y=0, w=100, h=100,
                 color="red", filled=False, fill_color="", page=0):
        super().__init__(page)
        self.shape_type = shape_type
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.color = color
        self.filled = filled
        self.fill_color = fill_color or color

    def get_bounds(self):
        return (self.x, self.y, self.w, self.h)

    def to_tuple(self):
        return (self.shape_type, {
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "color": self.color, "filled": self.filled,
            "fill_color": self.fill_color, "page": self.page
        })

    @classmethod
    def from_params(cls, etype, params):
        return cls(
            shape_type=etype,
            x=params.get("x", 0),
            y=params.get("y", 0),
            w=params.get("w", 100),
            h=params.get("h", 100),
            color=params.get("color", "red"),
            filled=params.get("filled", False),
            fill_color=params.get("fill_color", ""),
            page=params.get("page", 0)
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
            "page": self.page
        })

    @classmethod
    def from_params(cls, params):
        return cls(
            x1=params.get("x1", 0),
            y1=params.get("y1", 0),
            x2=params.get("x2", 100),
            y2=params.get("y2", 100),
            color=params.get("color", "red"),
            width=params.get("width", 2),
            page=params.get("page", 0)
        )


_ELEMENT_TYPE_MAP = {
    "text": TextElement,
    "image": ImageElement,
    "line": LineElement,
    "rect": ShapeElement,
    "ellipse": ShapeElement,
    "triangle": ShapeElement,
}


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
