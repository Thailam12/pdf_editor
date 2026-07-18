"""Page rotation operations.

Rotate selected or all pages by standard angles, or auto-detect
orientation from text layout.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Union

import fitz  # PyMuPDF


def rotate_pages(
    doc: fitz.Document,
    angle: int,
    pages: Optional[Sequence[int]] = None,
) -> None:
    """Rotate pages by *angle* degrees (must be a multiple of 90).

    Args:
        doc: Open PDF document (modified in-place).
        angle: Rotation in degrees: 0, 90, 180, or 270.
        pages: 0-based indices.  ``None`` rotates all pages.
    """
    angle = angle % 360
    if angle not in (0, 90, 180, 270):
        raise ValueError(f"Angle must be 0/90/180/270, got {angle}")
    targets = pages if pages is not None else range(len(doc))
    for p in targets:
        if 0 <= p < len(doc):
            page = doc[p]
            current = page.rotation
            target = (current + angle) % 360
            page.set_rotation(target)


def rotate_selected(
    source: Union[str, fitz.Document],
    output_path: str,
    page_rotations: Sequence[tuple],
) -> None:
    """Rotate individual pages to specific angles.

    Args:
        source: Input PDF path or document.
        output_path: Where to save the result.
        page_rotations: List of ``(page_index, angle)`` tuples.
    """
    doc = _open(source)
    for page_idx, angle in page_rotations:
        angle = angle % 360
        if angle not in (0, 90, 180, 270):
            continue
        if 0 <= page_idx < len(doc):
            doc[page_idx].set_rotation(angle)
    doc.save(output_path)


def auto_rotate_detect(
    doc: fitz.Document,
    threshold: float = 0.6,
) -> List[int]:
    """Detect page orientations and return suggested rotations.

    Analyses text blocks on each page.  If the majority of text lines
    are vertical the page is likely rotated 90 degrees.

    Returns:
        List of suggested rotation corrections (0 or 90) for each page.
    """
    suggestions: List[int] = []
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text_dict = page.get_text("dict")
        h_lines = 0
        v_lines = 0
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                first = spans[0]
                last = spans[-1]
                line_width = abs(last["bbox"][2] - first["bbox"][0])
                line_height = abs(line["bbox"][3] - line["bbox"][1])
                if line_width > line_height * 1.5:
                    h_lines += 1
                elif line_height > line_width * 1.5:
                    v_lines += 1
        total = h_lines + v_lines
        if total > 0 and v_lines / total > threshold:
            suggestions.append(90)
        else:
            suggestions.append(0)
    return suggestions


def apply_auto_rotations(
    doc: fitz.Document,
    suggestions: Optional[List[int]] = None,
) -> None:
    """Apply auto-detected rotations to correct page orientation."""
    if suggestions is None:
        suggestions = auto_rotate_detect(doc)
    for idx, angle in enumerate(suggestions):
        if angle != 0 and idx < len(doc):
            current = doc[idx].rotation
            doc[idx].set_rotation((current + angle) % 360)


def _open(src: Union[str, fitz.Document]) -> fitz.Document:
    if isinstance(src, fitz.Document):
        return src
    return fitz.open(str(src))
