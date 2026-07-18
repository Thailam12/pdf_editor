"""Large format printing (plotter) for engineering drawings, posters, and architectural plans."""

import os
import logging
import math
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LargeFormatSettings:
    paper_size: str = "ARCH D"
    orientation: str = "landscape"
    dpi: int = 300
    border_width_inches: float = 0.25
    crop_marks: bool = False
    bleed_inches: float = 0.125
    tiling: bool = False
    tile_rows: int = 1
    tile_cols: int = 1
    overlap_inches: float = 0.5
    color_management: str = "sRGB"
    line_weight_adjust: bool = True
    min_line_width_pt: float = 0.5
    scaling_mode: str = "fit"
    custom_width_inches: float = 0
    custom_height_inches: float = 0


PAPER_SIZES_INCHES = {
    "ARCH A": (12, 9), "ARCH B": (18, 12), "ARCH C": (24, 18),
    "ARCH D": (36, 24), "ARCH E": (48, 36), "ARCH E1": (42, 30),
    "ISO A0": (33.1, 46.8), "ISO A1": (23.4, 33.1), "ISO A2": (16.5, 23.4),
    "ISO A3": (11.7, 16.5), "ISO A4": (8.3, 11.7),
    "ANSI A": (8.5, 11), "ANSI B": (11, 17), "ANSI C": (17, 22),
    "ANSI D": (22, 34), "ANSI E": (34, 44),
    "B1": (27.8, 39.4), "B0": (39.4, 55.6),
    "Photo 4x6": (4, 6), "Photo 8x10": (8, 10),
    "Photo 11x14": (11, 14), "Photo 16x20": (16, 20),
    "Photo 20x24": (20, 24), "Photo 24x36": (24, 36),
}


@dataclass
class PlotterInfo:
    name: str = ""
    model: str = ""
    max_width_inches: float = 44
    max_length_inches: float = 0
    supported_media: list[str] = field(default_factory=list)
    dpi_range: tuple = (150, 2400)
    color_capable: bool = True
    is_loaded: bool = False


class LargeFormatPlotter:
    """Large format printing for engineering, architecture, and poster printing."""

    def __init__(self, settings: LargeFormatSettings = None):
        self._settings = settings or LargeFormatSettings()
        self._supported_sizes = PAPER_SIZES_INCHES

    def get_settings(self) -> LargeFormatSettings:
        return self._settings

    def update_settings(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)

    def get_paper_size_inches(self) -> tuple[float, float]:
        size = self._supported_sizes.get(self._settings.paper_size, (36, 24))
        if self._settings.custom_width_inches > 0 and self._settings.custom_height_inches > 0:
            return (self._settings.custom_width_inches, self._settings.custom_height_inches)
        w, h = size
        if self._settings.orientation == "landscape":
            return (max(w, h), min(w, h))
        return (min(w, h), max(w, h))

    def get_paper_size_points(self) -> tuple[float, float]:
        w, h = self.get_paper_size_inches()
        return (w * 72, h * 72)

    def get_printable_area(self) -> dict:
        pw, ph = self.get_paper_size_inches()
        b = self._settings.border_width_inches
        return {
            "width_inches": pw - 2 * b,
            "height_inches": ph - 2 * b,
            "width_points": (pw - 2 * b) * 72,
            "height_points": (ph - 2 * b) * 72,
            "x_offset": b,
            "y_offset": b,
        }

    def calculate_scaling(self, content_width: float, content_height: float) -> dict:
        pw, ph = self.get_printable_area()
        content_w_in = content_width / 72
        content_h_in = content_height / 72
        if self._settings.scaling_mode == "fit":
            scale = min(pw / content_w_in, ph / content_h_in) if content_w_in > 0 and content_h_in > 0 else 1.0
        elif self._settings.scaling_mode == "fill":
            scale = max(pw / content_w_in, ph / content_h_in) if content_w_in > 0 and content_h_in > 1 else 1.0
        elif self._settings.scaling_mode == "center":
            scale = 1.0
        else:
            scale = self._settings.scaling_mode.replace("%", "")
            try:
                scale = float(scale) / 100
            except (ValueError, TypeError):
                scale = 1.0
        return {
            "scale_factor": scale,
            "output_width_inches": content_w_in * scale,
            "output_height_inches": content_h_in * scale,
            "fits": content_w_in * scale <= pw and content_h_in * scale <= ph,
            "scaling_mode": self._settings.scaling_mode,
        }

    def calculate_tiling(self, content_width: float, content_height: float) -> dict:
        if not self._settings.tiling:
            return {"tiles": 1, "rows": 1, "cols": 1, "tile_size": (content_width, content_height)}
        pw, ph = self.get_printable_area()
        overlap = self._settings.overlap_inches * 72
        cols = max(1, math.ceil((content_width - overlap) / (pw - overlap)))
        rows = max(1, math.ceil((content_height - overlap) / (ph - overlap)))
        tile_w = (content_width + (cols - 1) * overlap) / cols
        tile_h = (content_height + (rows - 1) * overlap) / rows
        return {
            "tiles": rows * cols,
            "rows": rows,
            "cols": cols,
            "tile_width": tile_w,
            "tile_height": tile_h,
            "overlap_points": overlap,
        }

    def generate_crop_marks(self, page_width: float, page_height: float) -> list[dict]:
        marks = []
        offset = 0.25 * 72
        length = 0.375 * 72
        corners = [
            (0, 0, 1, 1), (page_width, 0, -1, 1),
            (0, page_height, 1, -1), (page_width, page_height, -1, -1),
        ]
        for cx, cy, dx, dy in corners:
            marks.append({"x": cx, "y": cy + dy * offset, "x2": cx, "y2": cy + dy * (offset + length)})
            marks.append({"x": cx + dx * offset, "y": cy, "x2": cx + dx * (offset + length), "y2": cy})
        return marks

    def estimate_ink_usage(self, coverage_pct: float = 30.0) -> dict:
        pw, ph = self.get_paper_size_inches()
        area_sq_inches = pw * ph
        coverage = coverage_pct / 100.0
        ml_per_sq_inch = 0.005
        return {
            "total_area_sq_inches": area_sq_inches,
            "coverage_pct": coverage_pct,
            "estimated_ml": area_sq_inches * coverage * ml_per_sq_inch,
            "paper_size": self._settings.paper_size,
        }

    def estimate_cost(self, media_cost_per_sqft: float = 2.50, coverage_pct: float = 30.0) -> dict:
        pw, ph = self.get_paper_size_inches()
        area_sqft = (pw * ph) / 144
        paper_cost = area_sqft * media_cost_per_sqft
        ink = self.estimate_ink_usage(coverage_pct)
        ink_cost = ink["estimated_ml"] * 0.05
        total = paper_cost + ink_cost
        return {
            "paper_cost": round(paper_cost, 2),
            "ink_cost": round(ink_cost, 2),
            "total_cost": round(total, 2),
            "area_sqft": round(area_sqft, 2),
        }

    def get_supported_sizes(self) -> list[dict]:
        sizes = []
        for name, (w, h) in sorted(self._supported_sizes.items()):
            sizes.append({
                "name": name,
                "width_inches": w,
                "height_inches": h,
                "width_points": w * 72,
                "height_points": h * 72,
            })
        return sizes

    def get_plotter_info(self) -> PlotterInfo:
        return PlotterInfo(
            name="PDFMind Large Format Plotter",
            model="PDFMind Virtual Plotter v1.0",
            max_width_inches=60,
            max_length_inches=200,
            supported_media=list(self._supported_sizes.keys()),
            dpi_range=(72, 2400),
            color_capable=True,
            is_loaded=True,
        )

    def prepare_print_job(self, pdf_path: str) -> dict:
        pw, ph = self.get_paper_size_inches()
        return {
            "source": pdf_path,
            "paper_size": self._settings.paper_size,
            "paper_inches": (pw, ph),
            "orientation": self._settings.orientation,
            "dpi": self._settings.dpi,
            "scaling": self._settings.scaling_mode,
            "crop_marks": self._settings.crop_marks,
            "tiling": self._settings.tiling,
            "printable_area": self.get_printable_area(),
            "estimated_cost": self.estimate_cost(),
        }
