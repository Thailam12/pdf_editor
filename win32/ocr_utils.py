# -*- coding: utf-8 -*-
"""OCR utilities.

Implements high-accuracy OCR using Tesseract (via pytesseract).

Main entrypoints:
- ocr_page_to_boxes(image, lang, config, dpi)
- convert_boxes_to_editor_text_elements(editor, page_number, boxes)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class OCRBox:
    text: str
    x1_px: int
    y1_px: int
    x2_px: int
    y2_px: int
    confidence: float | None = None


def _require_pytesseract() -> Any:
    try:
        import pytesseract  # type: ignore

        return pytesseract
    except Exception as e:
        raise RuntimeError(
            "pytesseract is not available. Install it and ensure Tesseract OCR is installed on the system."
        ) from e


def _preprocess_for_ocr(image):
    """Preprocess PIL image for OCR.

    Keeps it dependency-light: Pillow only.
    """
    # PIL imports inside to keep module import cheap.
    from PIL import Image, ImageOps, ImageFilter

    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")

    # Convert to grayscale
    gray = image.convert("L")

    # Slight smoothing then threshold via adaptive-ish approach using point threshold.
    # (We avoid numpy/opencv dependencies.)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))

    # Use autocontrast to help varying lighting.
    gray = ImageOps.autocontrast(gray)

    # Binarize using Otsu-like heuristic approximation: mid threshold.
    # Note: without numpy/opencv, we use a conservative threshold.
    # Tesseract is fairly robust; this helps most scans.
    threshold = 180
    bw = gray.point(lambda p: 255 if p > threshold else 0)

    return bw


def ocr_page_to_boxes(
    image,
    lang: str = "eng",
    config: Optional[str] = None,
) -> List[OCRBox]:
    """Run OCR on a PIL image and return boxes.

    Coordinates are in image pixel space with origin at top-left.
    """

    pytesseract = _require_pytesseract()

    if config is None:
        # -psm 6 assumes a uniform block of text.
        # Also enable word/box output.
        config = "--oem 1 --psm 6"

    processed = _preprocess_for_ocr(image)

    # Use image_to_data to get bounding boxes + confidence.
    data = pytesseract.image_to_data(
        processed,
        lang=lang,
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    boxes: List[OCRBox] = []

    n = len(data.get("text", []))
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue

        try:
            conf_raw = data.get("conf", [None])[i]
            conf: float | None
            if conf_raw is None:
                conf = None
            else:
                c = float(conf_raw)
                conf = c
        except Exception:
            conf = None

        # Skip very low confidence tokens.
        if conf is not None and conf < 30:
            continue

        x, y, w, h = (
            int(data["left"][i]),
            int(data["top"][i]),
            int(data["width"][i]),
            int(data["height"][i]),
        )

        boxes.append(
            OCRBox(
                text=txt,
                x1_px=x,
                y1_px=y,
                x2_px=x + w,
                y2_px=y + h,
                confidence=conf,
            )
        )

    # Sort top-to-bottom, left-to-right for stable insertion.
    boxes.sort(key=lambda b: (b.y1_px, b.x1_px))
    return boxes


def boxes_to_editor_text_elements(
    boxes: Sequence[OCRBox],
    page_number: int,
    img_width_px: int,
    img_height_px: int,
    page_width_pt: float,
    page_height_pt: float,
    font_name: str = "Arial",
    color: str = "#000000",
) -> List[Tuple[str, Dict[str, Any]]]:
    """Convert OCR boxes (pixel coords) to editor text element tuples.

    Editor uses points with origin at top-left-like canvas mapping.
    In this app, x/y for insert_textbox are treated as direct coordinates.

    We map pixel->point with simple linear scaling.
    """

    elements: List[Tuple[str, Dict[str, Any]]] = []

    # Avoid division by zero.
    sx = page_width_pt / max(1, img_width_px)
    sy = page_height_pt / max(1, img_height_px)

    for b in boxes:
        # Convert top-left pixel bbox to points.
        x_pt = b.x1_px * sx
        y_pt = b.y1_px * sy

        # Approx font size from bbox height.
        # Tesseract bbox height is in pixels; points use 72dpi.
        # The scale between OCR image DPI and point space is already included in sy.
        # So bbox height in points ~ (y2 - y1) * sy.
        bbox_h_pt = max(6.0, (b.y2_px - b.y1_px) * sy)
        font_size_pt = max(8, int(round(bbox_h_pt * 0.9)))

        elements.append(
            (
                "text",
                {
                    "text": b.text,
                    "x": float(x_pt),
                    "y": float(y_pt),
                    "size": int(font_size_pt),
                    "font_name": font_name,
                    "color": color,
                    "bold": False,
                    "italic": False,
                    "underline": False,
                    "alignment": "left",
                    "page": int(page_number),
                },
            )
        )

    return elements

