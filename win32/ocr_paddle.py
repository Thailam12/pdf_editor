# -*- coding: utf-8 -*-
"""PaddleOCR-based OCR utilities.

This module mirrors the interface expected by editor.py:
- ocr_image_to_boxes(pil_image, ...)-> List[OCRBox]

We return word-level boxes with pixel coordinates (top-left origin).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass(frozen=True)
class OCRBox:
    text: str
    x1_px: int
    y1_px: int
    x2_px: int
    y2_px: int
    confidence: float | None = None


def _require_paddleocr() -> Any:
    try:
        from paddleocr import PaddleOCR  # type: ignore

        return PaddleOCR
    except Exception as e:
        raise RuntimeError(
            "paddleocr is not available. Install paddleocr and its dependencies. "
            "Also ensure PaddlePaddle is installable for your platform."
        ) from e


_PADDLEOCR_INSTANCE: Any | None = None


def _get_ocr(lang: str = "en", use_gpu: bool = False) -> Any:
    global _PADDLEOCR_INSTANCE
    if _PADDLEOCR_INSTANCE is None:
        PaddleOCR = _require_paddleocr()
        _PADDLEOCR_INSTANCE = PaddleOCR(
            lang=lang,
            use_angle_cls=True,
            show_log=False,
            use_gpu=use_gpu,
        )
    return _PADDLEOCR_INSTANCE


def ocr_image_to_boxes(
    pil_image,
    *,
    lang: str = "en",
    use_gpu: bool = False,
) -> List[OCRBox]:
    """Run PaddleOCR on a PIL image and return word boxes."""

    # PaddleOCR can accept numpy arrays; to keep deps minimal, pass PIL -> bytes -> PIL in-place is unnecessary.
    # Most PaddleOCR installs rely on numpy.
    import numpy as np

    ocr = _get_ocr(lang=lang, use_gpu=use_gpu)

    # Convert PIL image to numpy (RGB)
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    img_np = np.array(pil_image)

    h, w = img_np.shape[:2]

    results = ocr.ocr(img_np, cls=True)
    # results: [ [ (box, (text, conf)), ... ] ]
    out: List[OCRBox] = []

    if not results:
        return out

    for line in results:
        for item in line:
            box, (txt, conf) = item
            if not txt:
                continue

            xs = [int(p[0]) for p in box]
            ys = [int(p[1]) for p in box]
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)

            # Clamp
            x1 = max(0, min(w, x1))
            x2 = max(0, min(w, x2))
            y1 = max(0, min(h, y1))
            y2 = max(0, min(h, y2))

            out.append(
                OCRBox(
                    text=str(txt).strip(),
                    x1_px=x1,
                    y1_px=y1,
                    x2_px=x2,
                    y2_px=y2,
                    confidence=float(conf) if conf is not None else None,
                )
            )

    out.sort(key=lambda b: (b.y1_px, b.x1_px))
    return out

