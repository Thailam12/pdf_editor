"""Image element for the PDF editor.

Handles image placement, filtering, cropping, and on-the-fly
replacements while preserving layout.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from engine.elements.base import BaseElement


class ImageFilter(Enum):
    NONE = "none"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    SATURATION = "saturation"
    BLUR = "blur"
    SHARPEN = "sharpen"
    GRAYSCALE = "grayscale"
    SEPIA = "sepia"
    INVERT = "invert"


@dataclass
class FilterConfig:
    """Configuration for a single image filter operation."""

    name: ImageFilter = ImageFilter.NONE
    amount: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name.value, "amount": self.amount}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FilterConfig:
        return cls(
            name=ImageFilter(data.get("name", "none")),
            amount=data.get("amount", 0.0),
        )


class ImageElement(BaseElement):
    """A placed image on a PDF page with filters, crop, and effects."""

    def __init__(
        self,
        page: int = 0,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        image_path: str = "",
        image_data: Optional[bytes] = None,
        rotation: float = 0.0,
        border_width: float = 0.0,
        border_color: Tuple[float, float, float, float] = (0, 0, 0, 1.0),
        shadow_offset: Tuple[float, float] = (0, 0),
        shadow_blur: float = 0.0,
        shadow_color: Tuple[float, float, float, float] = (0, 0, 0, 0.3),
        crop_rect: Optional[Tuple[float, float, float, float]] = None,
        flip_h: bool = False,
        flip_v: bool = False,
        filters: Optional[List[FilterConfig]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(page=page, bbox=bbox, **kwargs)
        self.image_path = image_path
        self._image_data = image_data
        self.rotation = rotation
        self.border_width = border_width
        self.border_color = border_color
        self.shadow_offset = shadow_offset
        self.shadow_blur = shadow_blur
        self.shadow_color = shadow_color
        self.crop_rect = crop_rect
        self.flip_h = flip_h
        self.flip_v = flip_v
        self.filters: List[FilterConfig] = filters or []

    @property
    def has_image_data(self) -> bool:
        return self._image_data is not None

    @property
    def aspect_ratio(self) -> float:
        x0, y0, x1, y1 = self.bbox
        w = abs(x1 - x0) or 1
        h = abs(y1 - y0) or 1
        return w / h

    def replace_image(self, new_path: str = "", new_data: Optional[bytes] = None) -> None:
        """Swap the image data while keeping position, size, and effects."""
        self.image_path = new_path
        self._image_data = new_data

    def add_filter(self, ftype: ImageFilter, amount: float = 0.0) -> None:
        self.filters.append(FilterConfig(name=ftype, amount=amount))

    def remove_filter(self, ftype: ImageFilter) -> None:
        self.filters = [f for f in self.filters if f.name != ftype]

    def clear_filters(self) -> None:
        self.filters.clear()

    def apply_brightness(self, amount: float) -> None:
        self.add_filter(ImageFilter.BRIGHTNESS, amount)

    def apply_contrast(self, amount: float) -> None:
        self.add_filter(ImageFilter.CONTRAST, amount)

    def apply_blur(self, radius: float) -> None:
        self.add_filter(ImageFilter.BLUR, radius)

    def apply_grayscale(self) -> None:
        self.add_filter(ImageFilter.GRAYSCALE, 1.0)

    def apply_sepia(self) -> None:
        self.add_filter(ImageFilter.SEPIA, 1.0)

    def apply_invert(self) -> None:
        self.add_filter(ImageFilter.INVERT, 1.0)

    def apply_sharpen(self, amount: float = 1.0) -> None:
        self.add_filter(ImageFilter.SHARPEN, amount)

    def apply_saturation(self, amount: float) -> None:
        self.add_filter(ImageFilter.SATURATION, amount)

    # -- transforms --------------------------------------------------------

    def rotate_to(self, angle: float) -> None:
        self.rotation = angle % 360.0

    def flip_horizontal(self) -> None:
        self.flip_h = not self.flip_h

    def flip_vertical(self) -> None:
        self.flip_v = not self.flip_v

    def skew(self, x_angle: float, y_angle: float) -> None:
        import math
        from engine.elements.base import AffineTransform
        sx = math.tan(math.radians(x_angle))
        sy = math.tan(math.radians(y_angle))
        self.apply_transform(AffineTransform(a=1, b=sy, c=sx, d=1, tx=0, ty=0))

    def set_crop(
        self, left: float, top: float, right: float, bottom: float
    ) -> None:
        self.crop_rect = (left, top, right, bottom)

    def clear_crop(self) -> None:
        self.crop_rect = None

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "type": "ImageElement",
            "image_path": self.image_path,
            "has_image_data": self.has_image_data,
            "rotation": self.rotation,
            "border_width": self.border_width,
            "border_color": list(self.border_color),
            "shadow_offset": list(self.shadow_offset),
            "shadow_blur": self.shadow_blur,
            "shadow_color": list(self.shadow_color),
            "crop_rect": list(self.crop_rect) if self.crop_rect else None,
            "flip_h": self.flip_h,
            "flip_v": self.flip_v,
            "filters": [f.to_dict() for f in self.filters],
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ImageElement:
        filters = [FilterConfig.from_dict(f) for f in data.get("filters", [])]
        crop = tuple(data["crop_rect"]) if data.get("crop_rect") else None
        elem = cls(
            page=data["page"],
            bbox=tuple(data["bbox"]),
            image_path=data.get("image_path", ""),
            rotation=data.get("rotation", 0.0),
            border_width=data.get("border_width", 0.0),
            border_color=tuple(data.get("border_color", [0, 0, 0, 1.0])),
            shadow_offset=tuple(data.get("shadow_offset", [0, 0])),
            shadow_blur=data.get("shadow_blur", 0.0),
            shadow_color=tuple(data.get("shadow_color", [0, 0, 0, 0.3])),
            crop_rect=crop,
            flip_h=data.get("flip_h", False),
            flip_v=data.get("flip_v", False),
            filters=filters,
            locked=data.get("locked", False),
            visible=data.get("visible", True),
            opacity=data.get("opacity", 1.0),
            name=data.get("name", ""),
            layer=data.get("layer", ""),
            z_index=data.get("z_index", 0),
        )
        elem.id = data.get("id", elem.id)
        return elem

    def clone(self) -> ImageElement:
        new = copy.deepcopy(self)
        new.id = uuid.uuid4().hex[:12]
        return new
