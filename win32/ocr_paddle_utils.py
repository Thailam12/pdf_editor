# -*- coding: utf-8 -*-
"""Helpers to integrate PaddleOCR boxes into the editor model."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from ocr_paddle import OCRBox
from ocr_utils import boxes_to_editor_text_elements


def paddle_boxes_to_editor_text_elements(
    boxes: Sequence[OCRBox],
    page_number: int,
    img_width_px: int,
    img_height_px: int,
    page_width_pt: float,
    page_height_pt: float,
    *,
    font_name: str = "Arial",
    color: str = "#000000",
):
    # Reuse the existing pixel->point mapping logic in ocr_utils
    normalized = boxes

    # ocr_utils expects its own OCRBox dataclass; but it only relies on attributes.
    # So we can pass objects with the same fields.
    return boxes_to_editor_text_elements(
        normalized,  # type: ignore[arg-type]
        page_number,
        img_width_px,
        img_height_px,
        page_width_pt,
        page_height_pt,
        font_name=font_name,
        color=color,
    )

