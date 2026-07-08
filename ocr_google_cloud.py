# -*- coding: utf-8 -*-
"""Google Cloud Vision OCR client.

This module provides OCR as a remote client (no local Tesseract exe required).

It exposes a function that accepts a PIL image and returns text blocks with
bounding boxes in pixel coordinates (top-left origin).

Note: Full "OCR 100%" accuracy depends on input quality and OCR configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class OCRGoogleBox:
    text: str
    x1_px: int
    y1_px: int
    x2_px: int
    y2_px: int
    confidence: float | None = None


def _require_google_client() -> Any:
    try:
        from google.cloud import vision  # type: ignore

        return vision
    except Exception as e:
        raise RuntimeError(
            "google-cloud-vision is not installed. Install dependencies in requirements.txt."
        ) from e


def _image_to_bytes_png(pil_image, *, quality: int = 95) -> bytes:
    """Convert PIL image to PNG bytes for Vision API."""
    import io
    from PIL import Image

    # Ensure RGB for consistent output
    if pil_image.mode not in ("RGB", "RGBA"):
        pil_image = pil_image.convert("RGB")

    buf = io.BytesIO()
    # PNG is lossless; use it for best OCR.
    pil_image.save(buf, format="PNG")
    return buf.getvalue()


def ocr_image_to_boxes(
    pil_image,
    *,
    lang_hint: Optional[str] = None,
    dpi: float = 300.0,
    locale_hint: Optional[str] = None,
) -> List[OCRGoogleBox]:
    """Run Google Cloud Vision OCR (text detection) and return boxes in pixel coords."""

    vision = _require_google_client()

    # Instantiate client; credentials are read from env GOOGLE_APPLICATION_CREDENTIALS.
    client = vision.ImageAnnotatorClient()

    img_bytes = _image_to_bytes_png(pil_image)
    from PIL import Image

    w_px, h_px = pil_image.size

    gimg = vision.Image(content=img_bytes)

    # Vision API: use document_text_detection for dense page layouts.
    # NOTE: language hints are not always supported for document_text_detection.
    response = client.document_text_detection(image=gimg, image_context=None)


    if getattr(response, "error", None):
        err = response.error
        raise RuntimeError(f"Google Vision API error: {getattr(err, 'message', str(err))}")

    annotation = response.full_text_annotation
    if annotation is None or not annotation.pages:
        return []

    boxes: List[OCRGoogleBox] = []

    # Walk word annotations.
    for page in annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    text = "".join([sym.text for sym in word.symbols if getattr(sym, "text", None)])
                    text = (text or "").strip()
                    if not text:
                        continue

                    # Each word has a bounding polygon with vertices in normalized-ish image coords.
                    # Vision returns coordinates in image coordinate space (pixels relative to the original image size).
                    # The API uses Vision "vertex" values in pixels.
                    verts = getattr(word.bounding_box, "vertices", None)
                    if not verts:
                        continue

                    xs = [int(v.x) for v in verts]
                    ys = [int(v.y) for v in verts]
                    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)

                    # Clamp
                    x1 = max(0, min(w_px, x1))
                    x2 = max(0, min(w_px, x2))
                    y1 = max(0, min(h_px, y1))
                    y2 = max(0, min(h_px, y2))

                    boxes.append(
                        OCRGoogleBox(
                            text=text,
                            x1_px=x1,
                            y1_px=y1,
                            x2_px=x2,
                            y2_px=y2,
                            confidence=None,
                        )
                    )

    boxes.sort(key=lambda b: (b.y1_px, b.x1_px))
    return boxes

