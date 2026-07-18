"""PDF reader with lazy loading, password support, and repair.

Wraps PyMuPDF with convenient abstractions for opening, inspecting,
and navigating PDF documents.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import fitz  # PyMuPDF


@dataclass
class ReaderOptions:
    """Configuration for opening a PDF."""
    password: str = ""
    repair: bool = False
    use_mmap: bool = False
    garbage_level: int = 0
    max_pages_lazy: int = 100


@dataclass
class PageInfo:
    """Lightweight metadata for a single page."""
    index: int
    width: float
    height: float
    rotation: int
    has_text: bool
    has_images: bool
    has_annotations: bool
    mediabox: List[float]
    cropbox: List[float]


class PDFReader:
    """High-level PDF reader with lazy page loading."""

    def __init__(self, source: Union[str, Path, bytes], options: Optional[ReaderOptions] = None) -> None:
        self._path: Optional[Path] = None
        self._data: Optional[bytes] = None
        self._options = options or ReaderOptions()
        self._doc: Optional[fitz.Document] = None
        self._page_cache: Dict[int, fitz.Page] = {}
        self._page_info_cache: Dict[int, PageInfo] = {}

        if isinstance(source, (str, Path)):
            self._path = Path(source)
            if not self._path.exists():
                raise FileNotFoundError(f"PDF not found: {self._path}")
        elif isinstance(source, bytes):
            self._data = source
        else:
            raise TypeError(f"Unsupported source type: {type(source)}")

    @property
    def doc(self) -> fitz.Document:
        if self._doc is None:
            self._open()
        return self._doc

    def _open(self) -> None:
        if self._data is not None:
            self._doc = fitz.open(stream=self._data, filetype="pdf")
        elif self._path is not None:
            if self._options.repair:
                self._repair_and_open()
            else:
                self._doc = fitz.open(str(self._path))

        if self._options.password:
            if self._doc.is_encrypted:
                ok = self._doc.authenticate(self._options.password)
                if not ok:
                    raise ValueError("Invalid password for encrypted PDF")

    def _repair_and_open(self) -> None:
        try:
            self._doc = fitz.open(str(self._path))
            self._doc.ez_save(os.devnull)
        except Exception:
            repaired_path = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            try:
                self._doc = fitz.open(str(self._path))
                self._doc.save(repaired_path.name, garbage=4, deflate=True)
                self._doc.close()
                self._doc = fitz.open(repaired_path.name)
            finally:
                os.unlink(repaired_path.name)

    def close(self) -> None:
        if self._doc is not None:
            self._doc.close()
            self._doc = None
        self._page_cache.clear()
        self._page_info_cache.clear()

    def __enter__(self) -> PDFReader:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @property
    def page_count(self) -> int:
        return len(self.doc)

    @property
    def is_encrypted(self) -> bool:
        return self.doc.is_encrypted

    @property
    def metadata(self) -> Dict[str, str]:
        return self.doc.metadata or {}

    def get_page(self, index: int) -> fitz.Page:
        if index < 0 or index >= len(self.doc):
            raise IndexError(f"Page index {index} out of range (0-{len(self.doc) - 1})")
        if index not in self._page_cache:
            self._page_cache[index] = self.doc[index]
        return self._page_cache[index]

    def get_page_info(self, index: int) -> PageInfo:
        if index in self._page_info_cache:
            return self._page_info_cache[index]
        page = self.get_page(index)
        text = page.get_text("text")
        info = PageInfo(
            index=index,
            width=page.rect.width,
            height=page.rect.height,
            rotation=page.rotation,
            has_text=bool(text.strip()),
            has_images=bool(page.get_images()),
            has_annotations=page.first_annot is not None,
            mediabox=list(page.mediabox),
            cropbox=list(page.cropbox),
        )
        self._page_info_cache[index] = info
        return info

    def get_toc(self, simple: bool = True) -> List[List]:
        return self.doc.get_toc(simple=simple)

    def get_page_text(self, index: int, mode: str = "text") -> str:
        return self.get_page(index).get_text(mode)

    def get_page_images(self, index: int) -> List[tuple]:
        return self.get_page(index).get_images(full=True)

    def get_toc_with_destinations(self) -> List[Dict[str, Any]]:
        toc = self.doc.get_toc(simple=False)
        results = []
        for entry in toc:
            level = entry[0]
            title = entry[1]
            page_num = entry[2] - 1 if len(entry) > 2 else 0
            results.append({
                "level": level,
                "title": title,
                "page": page_num,
                "kind": entry[3] if len(entry) > 3 else None,
                "dest": entry[4] if len(entry) > 4 else None,
            })
        return results

    def validate_structure(self) -> List[str]:
        issues: List[str] = []
        try:
            _ = self.page_count
        except Exception as e:
            issues.append(f"Cannot read page count: {e}")
        for i in range(min(self.page_count, 10)):
            try:
                _ = self.get_page(i)
            except Exception as e:
                issues.append(f"Page {i} cannot be loaded: {e}")
        return issues
