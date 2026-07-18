"""Utility for creating a blank document ("new file") for the editor.

The main PDF editing logic currently requires an existing PDF to open.
For "New (Temp)" we generate a blank one-page PDF placeholder that
users can draw on / add text/images to.

Implementation note:
- Coordinates in the editor are in points (72 pts per inch).
- Default page size here is A4 in points.
"""

from __future__ import annotations

import os
from typing import Optional

import pymupdf


def create_blank_pdf(
    path: str,
    *,
    page_width_points: int = 595,   # A4 width
    page_height_points: int = 842,  # A4 height
) -> str:
    """Create a blank one-page PDF at `path` and return the path."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    doc = pymupdf.open()
    page = doc.new_page(width=page_width_points, height=page_height_points)

    # Optional subtle background or watermark could be added here.
    # Keep blank for now.
    _ = page

    doc.save(path)
    doc.close()
    return path

