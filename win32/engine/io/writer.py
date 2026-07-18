"""PDF writer with compression, font embedding, and optimization.

Creates new PDFs or rewrites existing ones with full control over
structure, compression, and file size.
"""

from __future__ import annotations

import io
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import fitz  # PyMuPDF

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None  # type: ignore


@dataclass
class WriterOptions:
    """Configuration for PDF output."""
    compress: bool = True
    garbage_level: int = 4
    linear: bool = False
    pretty: bool = False
    optimize_images: bool = True
    max_image_size: int = 2 * 1024 * 1024
    embed_fonts: bool = True
    pdf_version: str = "1.7"


class PDFWriter:
    """High-level PDF writer supporting both new and rewritten documents."""

    def __init__(self, options: Optional[WriterOptions] = None) -> None:
        self._options = options or WriterOptions()
        self._doc = fitz.open()
        self._page_rect: Optional[fitz.Rect] = None

    def set_page_size(self, width: float, height: float) -> None:
        self._page_rect = fitz.Rect(0, 0, width, height)

    def new_page(
        self, width: float = 612, height: float = 792, index: int = -1
    ) -> fitz.Page:
        return self._doc.new_page(width=width, height=height)

    def add_page_from_source(
        self, source_doc: fitz.Document, page_index: int
    ) -> None:
        self._doc.insert_pdf(source_doc, from_page=page_index, to_page=page_index)

    def insert_text(
        self,
        page_index: int,
        text: str,
        rect: Tuple[float, float, float, float],
        fontsize: float = 12,
        fontname: str = "helv",
        color: Tuple[float, float, float] = (0, 0, 0),
        align: int = 0,
    ) -> fitz.Rect:
        page = self._doc[page_index]
        r = fitz.Rect(rect)
        rc = page.insert_textbox(
            r, text, fontsize=fontsize, fontname=fontname,
            color=color, align=align,
        )
        return r

    def insert_image(
        self,
        page_index: int,
        rect: Tuple[float, float, float, float],
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        keep_aspect: bool = True,
    ) -> None:
        page = self._doc[page_index]
        r = fitz.Rect(rect)
        if image_path:
            page.insert_image(r, filename=image_path, keep_proportion=keep_aspect)
        elif image_bytes:
            stream = io.BytesIO(image_bytes)
            page.insert_image(r, stream=stream, keep_proportion=keep_aspect)

    def draw_rectangle(
        self,
        page_index: int,
        rect: Tuple[float, float, float, float],
        fill: Optional[Tuple[float, float, float]] = None,
        stroke: Tuple[float, float, float] = (0, 0, 0),
        width: float = 1.0,
    ) -> None:
        page = self._doc[page_index]
        r = fitz.Rect(rect)
        page.draw_rect(r, fill=fill, color=stroke, width=width)

    def draw_line(
        self,
        page_index: int,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        color: Tuple[float, float, float] = (0, 0, 0),
        width: float = 1.0,
    ) -> None:
        page = self._doc[page_index]
        page.draw_line(fitz.Point(p1), fitz.Point(p2), color=color, width=width)

    def set_metadata(self, metadata: Dict[str, str]) -> None:
        self._doc.set_metadata(metadata)

    def set_toc(self, toc: List[List]) -> None:
        self._doc.set_toc(toc)

    def save(self, output_path: Union[str, Path]) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._doc.save(
            str(path),
            garbage=self._options.garbage_level,
            deflate=self._options.compress,
            deflate_level=6,
            linear=self._options.linear,
            pretty=self._options.pretty,
        )
        return path

    def save_to_bytes(self) -> bytes:
        buf = io.BytesIO()
        self._doc.save(
            buf,
            garbage=self._options.garbage_level,
            deflate=self._options.compress,
            linear=self._options.linear,
        )
        return buf.getvalue()

    def get_file_size_estimate(self) -> int:
        return len(self.save_to_bytes())

    def optimize_file_size(self, output_path: Union[str, Path]) -> Path:
        path = Path(output_path)
        self._doc.save(
            str(path),
            garbage=4,
            deflate=True,
            deflate_level=9,
            clean=True,
            incremental=False,
        )
        smaller = fitz.open(str(path))
        final = fitz.open()
        final.insert_pdf(smaller)
        smaller.close()
        final.save(
            str(path),
            garbage=4,
            deflate=True,
            deflate_level=9,
        )
        final.close()
        return path

    @property
    def page_count(self) -> int:
        return len(self._doc)

    @property
    def doc(self) -> fitz.Document:
        return self._doc

    def close(self) -> None:
        if self._doc:
            self._doc.close()

    def __enter__(self) -> PDFWriter:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
