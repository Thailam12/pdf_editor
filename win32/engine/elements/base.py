"""Base element class for all PDF editor elements.

Every visual object placed on a page derives from BaseElement, which
carries common spatial properties, visibility state, and serialization.
"""

from __future__ import annotations

import copy
import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AffineTransform:
    """2-D affine transform represented as a 3x3 matrix (row-major).

    The matrix layout used here matches PDF coordinate conventions:
        | a  b  0 |
        | c  d  0 |
        | tx ty 1 |
    """

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 0.0
    tx: float = 0.0
    ty: float = 0.0

    # -- factory helpers ---------------------------------------------------

    @classmethod
    def identity(cls) -> AffineTransform:
        return cls()

    @classmethod
    def translation(cls, dx: float, dy: float) -> AffineTransform:
        return cls(tx=dx, ty=dy)

    @classmethod
    def scaling(cls, sx: float, sy: float) -> AffineTransform:
        return cls(a=sx, d=sy)

    @classmethod
    def rotation(cls, angle_rad: float, cx: float = 0, cy: float = 0) -> AffineTransform:
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        return cls(
            a=cos_a, b=sin_a,
            c=-sin_a, d=cos_a,
            tx=cx - cx * cos_a + cy * sin_a,
            ty=cy - cx * sin_a - cy * cos_a,
        )

    @classmethod
    def from_matrix(cls, matrix: List[float]) -> AffineTransform:
        if len(matrix) != 6:
            raise ValueError("Matrix must have 6 elements [a,b,c,d,tx,ty]")
        return cls(a=matrix[0], b=matrix[1], c=matrix[2],
                   d=matrix[3], tx=matrix[4], ty=matrix[5])

    # -- operations --------------------------------------------------------

    def apply_to_point(self, x: float, y: float) -> Tuple[float, float]:
        nx = x * self.a + y * self.c + self.tx
        ny = x * self.b + y * self.d + self.ty
        return (nx, ny)

    def compose(self, other: AffineTransform) -> AffineTransform:
        return AffineTransform(
            a=self.a * other.a + self.b * other.c,
            b=self.a * other.b + self.b * other.d,
            c=self.c * other.a + self.d * other.c,
            d=self.c * other.b + self.d * other.d,
            tx=self.tx * other.a + self.ty * other.c + other.tx,
            ty=self.tx * other.b + self.ty * other.d + other.ty,
        )

    def to_list(self) -> List[float]:
        return [self.a, self.b, self.c, self.d, self.tx, self.ty]

    @property
    def determinant(self) -> float:
        return self.a * self.d - self.b * self.c

    @property
    def is_identity(self) -> bool:
        return (abs(self.a - 1) < 1e-9 and abs(self.d - 1) < 1e-9
                and abs(self.b) < 1e-9 and abs(self.c) < 1e-9
                and abs(self.tx) < 1e-9 and abs(self.ty) < 1e-9)


class BaseElement:
    """Abstract base for every visual element on a PDF page.

    Sub-classes *must* implement at least ``clone`` and ``to_dict``.
    ``from_dict`` is a classmethod counterpart of ``to_dict``.
    """

    _counter: int = 0

    def __init__(
        self,
        page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        locked: bool = False,
        visible: bool = True,
        opacity: float = 1.0,
        name: str = "",
        layer: str = "",
        z_index: int = 0,
    ) -> None:
        BaseElement._counter += 1
        self.id: str = uuid.uuid4().hex[:12]
        self.page: int = page
        self.bbox: Tuple[float, float, float, float] = bbox or (0, 0, 0, 0)
        self.locked: bool = locked
        self.visible: bool = visible
        self.opacity: float = max(0.0, min(1.0, opacity))
        self.name: str = name or f"element_{BaseElement._counter}"
        self.layer: str = layer
        self.z_index: int = z_index
        self.transform: AffineTransform = AffineTransform.identity()

    # -- spatial -----------------------------------------------------------

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Return (x0, y0, x1, y1) after applying the current transform."""
        x0, y0, x1, y1 = self.bbox
        corners = [
            self.transform.apply_to_point(x0, y0),
            self.transform.apply_to_point(x1, y0),
            self.transform.apply_to_point(x1, y1),
            self.transform.apply_to_point(x0, y1),
        ]
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        return (min(xs), min(ys), max(xs), max(ys))

    def contains_point(self, x: float, y: float, tolerance: float = 2.0) -> bool:
        bx0, by0, bx1, by1 = self.get_bounds()
        return (bx0 - tolerance <= x <= bx1 + tolerance
                and by0 - tolerance <= y <= by1 + tolerance)

    def intersects(self, other: BaseElement) -> bool:
        ax0, ay0, ax1, ay1 = self.get_bounds()
        bx0, by0, bx1, by1 = other.get_bounds()
        return ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0

    def get_center(self) -> Tuple[float, float]:
        x0, y0, x1, y1 = self.get_bounds()
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    def get_area(self) -> float:
        x0, y0, x1, y1 = self.get_bounds()
        return max(0, x1 - x0) * max(0, y1 - y0)

    # -- mutation ----------------------------------------------------------

    def move(self, dx: float, dy: float) -> None:
        x0, y0, x1, y1 = self.bbox
        self.bbox = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)

    def resize(self, dw: float, dh: float) -> None:
        x0, y0, x1, y1 = self.bbox
        self.bbox = (x0, y0, x1 + dw, y1 + dh)

    def apply_transform(self, matrix: AffineTransform) -> None:
        self.transform = self.transform.compose(matrix)

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": type(self).__name__,
            "id": self.id,
            "page": self.page,
            "bbox": list(self.bbox),
            "locked": self.locked,
            "visible": self.visible,
            "opacity": self.opacity,
            "name": self.name,
            "layer": self.layer,
            "z_index": self.z_index,
            "transform": self.transform.to_list(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaseElement:
        elem = cls(
            page=data["page"],
            bbox=tuple(data["bbox"]),
            locked=data.get("locked", False),
            visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0),
            name=data.get("name", ""),
            layer=data.get("layer", ""),
            z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        if "transform" in data:
            elem.transform = AffineTransform.from_matrix(data["transform"])
        return elem

    # -- cloning -----------------------------------------------------------

    def clone(self) -> BaseElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} id={self.id} page={self.page} "
            f"bbox={self.bbox} name={self.name!r}>"
        )
