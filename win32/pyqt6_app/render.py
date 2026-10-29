# -*- coding: utf-8 -*-
"""PyQt6 rendering helpers: turn PyMuPDF pages into QPixmap/QImage."""
import pymupdf
from PyQt6.QtGui import QImage, QPixmap


def pixmap_to_qimage(pix: "pymupdf.Pixmap") -> QImage:
    """Convert a PyMuPDF pixmap (RGB or RGBA) into a deep-copied QImage."""
    if pix.alpha:
        fmt = QImage.Format.Format_RGBA8888
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
    else:
        fmt = QImage.Format.Format_RGB888
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
    # copy() detaches from the pixmap buffer which is freed on GC.
    return image.copy()


def render_page(page: "pymupdf.Page", scale: float = 1.0) -> QPixmap:
    """Render a single PDF page to a QPixmap at the given zoom scale."""
    matrix = pymupdf.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return QPixmap.fromImage(pixmap_to_qimage(pix))


def render_page_size(page: "pymupdf.Page", scale: float = 1.0):
    """Return the rendered (width, height) of a page without rasterizing."""
    rect = page.rect
    return int(rect.width * scale), int(rect.height * scale)
