"""Vector / shape elements for the PDF editor.

Provides path, rectangle, ellipse, triangle, polygon, star, arrow,
callout, and line primitives.
"""

from __future__ import annotations

import copy
import math
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from engine.elements.base import BaseElement


class PathCommand(Enum):
    MOVE = "M"
    LINE = "L"
    CURVE = "C"
    CLOSE = "Z"


@dataclass
class PathPoint:
    x: float = 0.0
    y: float = 0.0
    cx1: float = 0.0
    cy1: float = 0.0
    cx2: float = 0.0
    cy2: float = 0.0

    def to_dict(self) -> List[float]:
        return [self.x, self.y, self.cx1, self.cy1, self.cx2, self.cy2]

    @classmethod
    def from_dict(cls, data: List[float]) -> PathPoint:
        d = data + [0.0] * (6 - len(data))
        return cls(x=d[0], y=d[1], cx1=d[2], cy1=d[3], cx2=d[4], cy2=d[5])


class PathElement(BaseElement):
    """Arbitrary path built from move/line/curve/close commands."""

    def __init__(
        self,
        page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        commands: Optional[List[Tuple[PathCommand, List[PathPoint]]]] = None,
        fill_color: Optional[Tuple[float, float, float, float]] = None,
        stroke_color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        stroke_width: float = 1.0,
        filled: bool = True,
        stroked: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kwargs)
        self.commands: List[Tuple[PathCommand, List[PathPoint]]] = commands or []
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.filled = filled
        self.stroked = stroked

    def move_to(self, x: float, y: float) -> None:
        self.commands.append((PathCommand.MOVE, [PathPoint(x, y)]))

    def line_to(self, x: float, y: float) -> None:
        self.commands.append((PathCommand.LINE, [PathPoint(x, y)]))

    def curve_to(self, cx1: float, cy1: float, cx2: float, cy2: float,
                 x: float, y: float) -> None:
        self.commands.append(
            (PathCommand.CURVE, [PathPoint(x, y, cx1, cy1, cx2, cy2)])
        )

    def close(self) -> None:
        self.commands.append((PathCommand.CLOSE, []))

    def _compute_bbox(self) -> Tuple[float, float, float, float]:
        valid_xs: List[float] = []
        valid_ys: List[float] = []
        for cmd, points in self.commands:
            for pt in points:
                valid_xs.append(pt.x)
                valid_ys.append(pt.y)
        if not valid_xs:
            return (0, 0, 0, 0)
        return (min(valid_xs), min(valid_ys), max(valid_xs), max(valid_ys))

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        cmds = []
        for cmd, points in self.commands:
            cmds.append({"cmd": cmd.value, "points": [p.to_dict() for p in points]})
        d.update({
            "type": "PathElement",
            "commands": cmds,
            "fill_color": list(self.fill_color) if self.fill_color else None,
            "stroke_color": list(self.stroke_color),
            "stroke_width": self.stroke_width,
            "filled": self.filled,
            "stroked": self.stroked,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PathElement:
        commands = []
        for c in data.get("commands", []):
            cmd = PathCommand(c["cmd"])
            points = [PathPoint.from_dict(p) for p in c.get("points", [])]
            commands.append((cmd, points))
        fill = tuple(data["fill_color"]) if data.get("fill_color") else None
        elem = cls(
            page=data["page"],
            bbox=tuple(data["bbox"]),
            commands=commands,
            fill_color=fill,
            stroke_color=tuple(data.get("stroke_color", [0, 0, 0, 1.0])),
            stroke_width=data.get("stroke_width", 1.0),
            filled=data.get("filled", True),
            stroked=data.get("stroked", True),
            locked=data.get("locked", False),
            visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0),
            name=data.get("name", ""),
            layer=data.get("layer", ""),
            z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> PathElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new


class RectangleElement(BaseElement):
    def __init__(
        self, page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        fill_color: Optional[Tuple[float, float, float, float]] = None,
        stroke_color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        stroke_width: float = 1.0,
        corner_radius: float = 0.0,
        filled: bool = True, stroked: bool = True, **kw: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kw)
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.corner_radius = corner_radius
        self.filled = filled
        self.stroked = stroked

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "RectangleElement",
            "fill_color": list(self.fill_color) if self.fill_color else None,
            "stroke_color": list(self.stroke_color),
            "stroke_width": self.stroke_width,
            "corner_radius": self.corner_radius,
            "filled": self.filled, "stroked": self.stroked,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RectangleElement:
        fill = tuple(data["fill_color"]) if data.get("fill_color") else None
        elem = cls(
            page=data["page"], bbox=tuple(data["bbox"]),
            fill_color=fill,
            stroke_color=tuple(data.get("stroke_color", [0, 0, 0, 1.0])),
            stroke_width=data.get("stroke_width", 1.0),
            corner_radius=data.get("corner_radius", 0.0),
            filled=data.get("filled", True), stroked=data.get("stroked", True),
            locked=data.get("locked", False), visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0), name=data.get("name", ""),
            layer=data.get("layer", ""), z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> RectangleElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new


class EllipseElement(BaseElement):
    def __init__(
        self, page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        fill_color: Optional[Tuple[float, float, float, float]] = None,
        stroke_color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        stroke_width: float = 1.0,
        filled: bool = True, stroked: bool = True, **kw: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kw)
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.filled = filled
        self.stroked = stroked

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "EllipseElement",
            "fill_color": list(self.fill_color) if self.fill_color else None,
            "stroke_color": list(self.stroke_color),
            "stroke_width": self.stroke_width,
            "filled": self.filled, "stroked": self.stroked,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EllipseElement:
        fill = tuple(data["fill_color"]) if data.get("fill_color") else None
        elem = cls(
            page=data["page"], bbox=tuple(data["bbox"]), fill_color=fill,
            stroke_color=tuple(data.get("stroke_color", [0, 0, 0, 1.0])),
            stroke_width=data.get("stroke_width", 1.0),
            filled=data.get("filled", True), stroked=data.get("stroked", True),
            locked=data.get("locked", False), visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0), name=data.get("name", ""),
            layer=data.get("layer", ""), z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> EllipseElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new


class TriangleElement(BaseElement):
    def __init__(
        self, page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        points: Optional[List[Tuple[float, float]]] = None,
        fill_color: Optional[Tuple[float, float, float, float]] = None,
        stroke_color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        stroke_width: float = 1.0,
        filled: bool = True, stroked: bool = True, **kw: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kw)
        if points and len(points) == 3:
            self._points = points
        else:
            x0, y0, x1, y1 = self.bbox
            self._points = [(x0, y1), ((x0 + x1) / 2, y0), (x1, y1)]
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.filled = filled
        self.stroked = stroked

    @property
    def points(self) -> List[Tuple[float, float]]:
        return list(self._points)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "TriangleElement",
            "points": [list(p) for p in self._points],
            "fill_color": list(self.fill_color) if self.fill_color else None,
            "stroke_color": list(self.stroke_color),
            "stroke_width": self.stroke_width,
            "filled": self.filled, "stroked": self.stroked,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TriangleElement:
        fill = tuple(data["fill_color"]) if data.get("fill_color") else None
        pts = [tuple(p) for p in data.get("points", [])]
        elem = cls(
            page=data["page"], bbox=tuple(data["bbox"]), points=pts,
            fill_color=fill,
            stroke_color=tuple(data.get("stroke_color", [0, 0, 0, 1.0])),
            stroke_width=data.get("stroke_width", 1.0),
            filled=data.get("filled", True), stroked=data.get("stroked", True),
            locked=data.get("locked", False), visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0), name=data.get("name", ""),
            layer=data.get("layer", ""), z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> TriangleElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new


class PolygonElement(BaseElement):
    def __init__(
        self, page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        points: Optional[List[Tuple[float, float]]] = None,
        fill_color: Optional[Tuple[float, float, float, float]] = None,
        stroke_color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        stroke_width: float = 1.0,
        filled: bool = True, stroked: bool = True, **kw: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kw)
        self._points: List[Tuple[float, float]] = points or []
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.filled = filled
        self.stroked = stroked

    @property
    def points(self) -> List[Tuple[float, float]]:
        return list(self._points)

    @property
    def num_sides(self) -> int:
        return len(self._points)

    def add_point(self, x: float, y: float) -> None:
        self._points.append((x, y))

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "PolygonElement",
            "points": [list(p) for p in self._points],
            "fill_color": list(self.fill_color) if self.fill_color else None,
            "stroke_color": list(self.stroke_color),
            "stroke_width": self.stroke_width,
            "filled": self.filled, "stroked": self.stroked,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PolygonElement:
        fill = tuple(data["fill_color"]) if data.get("fill_color") else None
        pts = [tuple(p) for p in data.get("points", [])]
        elem = cls(
            page=data["page"], bbox=tuple(data["bbox"]), points=pts,
            fill_color=fill,
            stroke_color=tuple(data.get("stroke_color", [0, 0, 0, 1.0])),
            stroke_width=data.get("stroke_width", 1.0),
            filled=data.get("filled", True), stroked=data.get("stroked", True),
            locked=data.get("locked", False), visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0), name=data.get("name", ""),
            layer=data.get("layer", ""), z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> PolygonElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new


class StarElement(BaseElement):
    def __init__(
        self, page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        num_points: int = 5, inner_radius_ratio: float = 0.4,
        fill_color: Optional[Tuple[float, float, float, float]] = None,
        stroke_color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        stroke_width: float = 1.0,
        filled: bool = True, stroked: bool = True, **kw: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kw)
        self.num_points = max(3, num_points)
        self.inner_radius_ratio = max(0.1, min(0.9, inner_radius_ratio))
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.filled = filled
        self.stroked = stroked

    def get_star_points(self, cx: float, cy: float, outer_r: float) -> List[Tuple[float, float]]:
        inner_r = outer_r * self.inner_radius_ratio
        pts: List[Tuple[float, float]] = []
        for i in range(self.num_points * 2):
            angle = math.radians(i * 180 / self.num_points - 90)
            r = outer_r if i % 2 == 0 else inner_r
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        return pts

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "StarElement",
            "num_points": self.num_points,
            "inner_radius_ratio": self.inner_radius_ratio,
            "fill_color": list(self.fill_color) if self.fill_color else None,
            "stroke_color": list(self.stroke_color),
            "stroke_width": self.stroke_width,
            "filled": self.filled, "stroked": self.stroked,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StarElement:
        fill = tuple(data["fill_color"]) if data.get("fill_color") else None
        elem = cls(
            page=data["page"], bbox=tuple(data["bbox"]),
            num_points=data.get("num_points", 5),
            inner_radius_ratio=data.get("inner_radius_ratio", 0.4),
            fill_color=fill,
            stroke_color=tuple(data.get("stroke_color", [0, 0, 0, 1.0])),
            stroke_width=data.get("stroke_width", 1.0),
            filled=data.get("filled", True), stroked=data.get("stroked", True),
            locked=data.get("locked", False), visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0), name=data.get("name", ""),
            layer=data.get("layer", ""), z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> StarElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new


class ArrowElement(BaseElement):
    def __init__(
        self, page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        tail: Tuple[float, float] = (0, 0),
        head: Tuple[float, float] = (100, 0),
        head_size: float = 15.0,
        head_style: str = "triangle",
        stroke_color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        stroke_width: float = 2.0,
        **kw: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kw)
        self.tail = tail
        self.head = head
        self.head_size = head_size
        self.head_style = head_style
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width

    @property
    def length(self) -> float:
        return math.hypot(self.head[0] - self.tail[0], self.head[1] - self.tail[1])

    @property
    def angle(self) -> float:
        return math.degrees(math.atan2(
            self.head[1] - self.tail[1], self.head[0] - self.tail[0]
        ))

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "ArrowElement",
            "tail": list(self.tail), "head": list(self.head),
            "head_size": self.head_size, "head_style": self.head_style,
            "stroke_color": list(self.stroke_color),
            "stroke_width": self.stroke_width,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ArrowElement:
        elem = cls(
            page=data["page"], bbox=tuple(data["bbox"]),
            tail=tuple(data.get("tail", [0, 0])),
            head=tuple(data.get("head", [100, 0])),
            head_size=data.get("head_size", 15.0),
            head_style=data.get("head_style", "triangle"),
            stroke_color=tuple(data.get("stroke_color", [0, 0, 0, 1.0])),
            stroke_width=data.get("stroke_width", 2.0),
            locked=data.get("locked", False), visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0), name=data.get("name", ""),
            layer=data.get("layer", ""), z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> ArrowElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new


class CalloutElement(BaseElement):
    def __init__(
        self, page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        tail_point: Tuple[float, float] = (0, 0),
        tail_bend: Optional[Tuple[float, float]] = None,
        fill_color: Optional[Tuple[float, float, float, float]] = None,
        stroke_color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        stroke_width: float = 1.0,
        corner_radius: float = 8.0,
        **kw: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kw)
        self.tail_point = tail_point
        self.tail_bend = tail_bend
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.corner_radius = corner_radius

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "CalloutElement",
            "tail_point": list(self.tail_point),
            "tail_bend": list(self.tail_bend) if self.tail_bend else None,
            "fill_color": list(self.fill_color) if self.fill_color else None,
            "stroke_color": list(self.stroke_color),
            "stroke_width": self.stroke_width,
            "corner_radius": self.corner_radius,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CalloutElement:
        fill = tuple(data["fill_color"]) if data.get("fill_color") else None
        bend = tuple(data["tail_bend"]) if data.get("tail_bend") else None
        elem = cls(
            page=data["page"], bbox=tuple(data["bbox"]),
            tail_point=tuple(data.get("tail_point", [0, 0])),
            tail_bend=bend, fill_color=fill,
            stroke_color=tuple(data.get("stroke_color", [0, 0, 0, 1.0])),
            stroke_width=data.get("stroke_width", 1.0),
            corner_radius=data.get("corner_radius", 8.0),
            locked=data.get("locked", False), visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0), name=data.get("name", ""),
            layer=data.get("layer", ""), z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> CalloutElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new


class LineElement(BaseElement):
    def __init__(
        self, page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        x1: float = 0, y1: float = 0, x2: float = 100, y2: float = 0,
        color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        width: float = 1.0,
        dash_style: str = "solid",
        **kw: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kw)
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.color = color
        self.width = width
        self.dash_style = dash_style

    @property
    def length(self) -> float:
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "LineElement",
            "x1": self.x1, "y1": self.y1,
            "x2": self.x2, "y2": self.y2,
            "color": list(self.color),
            "width": self.width, "dash_style": self.dash_style,
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LineElement:
        elem = cls(
            page=data["page"], bbox=tuple(data["bbox"]),
            x1=data.get("x1", 0), y1=data.get("y1", 0),
            x2=data.get("x2", 100), y2=data.get("y2", 0),
            color=tuple(data.get("color", [0, 0, 0, 1.0])),
            width=data.get("width", 1.0),
            dash_style=data.get("dash_style", "solid"),
            locked=data.get("locked", False), visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0), name=data.get("name", ""),
            layer=data.get("layer", ""), z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> LineElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new
