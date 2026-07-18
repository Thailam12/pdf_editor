"""Page cropping operations.

Set and manipulate PDF page boxes (MediaBox, CropBox, etc.) and
provide auto-crop functionality for removing white margins.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple, Union

import fitz  # PyMuPDF


BOX_NAMES = ("MediaBox", "CropBox", "BleedBox", "TrimBox", "ArtBox")


def set_media_box(
    doc: fitz.Document, page_index: int,
    rect: Tuple[float, float, float, float],
) -> None:
    page = doc[page_index]
    page.set_mediabox(fitz.Rect(rect))


def set_crop_box(
    doc: fitz.Document, page_index: int,
    rect: Tuple[float, float, float, float],
) -> None:
    page = doc[page_index]
    page.set_cropbox(fitz.Rect(rect))


def set_trim_box(
    doc: fitz.Document, page_index: int,
    rect: Tuple[float, float, float, float],
) -> None:
    page = doc[page_index]
    page.set_trimbox(fitz.Rect(rect))


def set_bleed_box(
    doc: fitz.Document, page_index: int,
    rect: Tuple[float, float, float, float],
) -> None:
    page = doc[page_index]
    page.set_bleedbox(fitz.Rect(rect))


def set_art_box(
    doc: fitz.Document, page_index: int,
    rect: Tuple[float, float, float, float],
) -> None:
    page = doc[page_index]
    page.set_artbox(fitz.Rect(rect))


def crop_to_selection(
    doc: fitz.Document,
    page_index: int,
    rect: Tuple[float, float, float, float],
    box: str = "CropBox",
) -> None:
    """Set a page box to the given rectangle coordinates."""
    setter = _get_box_setter(box)
    setter(doc, page_index, rect)


def crop_to_content(
    doc: fitz.Document,
    page_index: int,
    margin: float = 0.0,
    box: str = "CropBox",
) -> Tuple[float, float, float, float]:
    """Crop a page to its visible content bounding box.

    Returns the applied crop rectangle.
    """
    page = doc[page_index]
    content_rect = page.get_contents()
    text_rect = page.get_text("text", clip=None)
    text_bbox = page.get_text_bbox("text")

    drawings = page.get_drawings()
    if drawings:
        draw_rects = [d["rect"] for d in drawings if "rect" in d]
        if draw_rects:
            combined = draw_rects[0]
            for r in draw_rects[1:]:
                combined = combined | r
            if text_bbox:
                text_bbox = fitz.Rect(text_bbox) | combined
            else:
                text_bbox = combined

    if text_bbox is None or fitz.Rect(text_bbox).is_empty:
        text_bbox = page.rect

    r = fitz.Rect(text_bbox)
    r = fitz.Rect(
        r.x0 - margin, r.y0 - margin,
        r.x1 + margin, r.y1 + margin,
    )
    r = r & page.rect
    setter = _get_box_setter(box)
    setter(doc, page_index, (r.x0, r.y0, r.x1, r.y1))
    return (r.x0, r.y0, r.x1, r.y1)


def auto_crop_whitespace(
    doc: fitz.Document,
    pages: Optional[Sequence[int]] = None,
    threshold: int = 250,
    margin: float = 5.0,
    box: str = "CropBox",
) -> list:
    """Remove white margins from pages by detecting content bounds.

    Args:
        doc: Open PDF.
        pages: Page indices; ``None`` = all pages.
        threshold: Pixel brightness threshold (0-255) for white detection.
        margin: Padding around detected content in points.
        box: Which page box to modify.

    Returns:
        List of applied crop rectangles per page.
    """
    targets = pages if pages is not None else range(len(doc))
    applied = []
    for p in targets:
        page = doc[p]
        rect = _detect_content_bbox(page, threshold)
        if rect is None:
            applied.append(page.rect)
            continue
        r = fitz.Rect(rect)
        r = fitz.Rect(
            r.x0 - margin, r.y0 - margin,
            r.x1 + margin, r.y1 + margin,
        )
        r = r & page.rect
        setter = _get_box_setter(box)
        setter(doc, p, (r.x0, r.y0, r.x1, r.y1))
        applied.append((r.x0, r.y0, r.x1, r.y1))
    return applied


def get_page_box(
    doc: fitz.Document, page_index: int, box: str = "CropBox"
) -> Tuple[float, float, float, float]:
    """Read the current value of a page box."""
    page = doc[page_index]
    box_lower = box.lower()
    if box_lower == "mediabox":
        r = page.mediabox
    elif box_lower == "cropbox":
        r = page.cropbox
    elif box_lower == "bleedbox":
        r = page.bleedbox
    elif box_lower == "trimbox":
        r = page.trimbox
    elif box_lower == "artbox":
        r = page.artbox
    else:
        r = page.cropbox
    return (r.x0, r.y0, r.x1, r.y1)


def _detect_content_bbox(
    page: fitz.Page, threshold: int = 250
) -> Optional[Tuple[float, float, float, float]]:
    """Detect the bounding box of non-white content on a page."""
    text_bbox = page.get_text_bbox("text")
    drawings = page.get_drawings()
    draw_rects = [d["rect"] for d in drawings if "rect" in d]

    image_list = page.get_images(full=True)
    image_rects = []
    for img in image_list:
        xref = img[0]
        rects = page.get_image_rects(xref)
        image_rects.extend(rects)

    all_rects = []
    if text_bbox:
        all_rects.append(fitz.Rect(text_bbox))
    for r in draw_rects:
        all_rects.append(fitz.Rect(r))
    for r in image_rects:
        all_rects.append(fitz.Rect(r))

    if not all_rects:
        return None

    combined = all_rects[0]
    for r in all_rects[1:]:
        combined = combined | r
    return (combined.x0, combined.y0, combined.x1, combined.y1)


def _get_box_setter(box: str):
    mapping = {
        "mediabox": set_media_box,
        "cropbox": set_crop_box,
        "bleedbox": set_bleed_box,
        "trimbox": set_trim_box,
        "artbox": set_art_box,
    }
    return mapping.get(box.lower(), set_crop_box)
