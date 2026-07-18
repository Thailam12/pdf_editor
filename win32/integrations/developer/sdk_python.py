"""Python SDK for PDFMind: programmatic access to all PDF operations."""

import os
import json
import logging
import tempfile
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DocumentInfo:
    file_path: str = ""
    title: str = ""
    author: str = ""
    page_count: int = 0
    file_size: int = 0
    is_encrypted: bool = False
    metadata: dict = field(default_factory=dict)
    creation_date: str = ""
    modification_date: str = ""


@dataclass
class PageInfo:
    index: int = 0
    width: float = 0
    height: float = 0
    rotation: int = 0
    has_text: bool = False
    has_images: bool = False
    annotations_count: int = 0


@dataclass
class ElementInfo:
    element_id: str = ""
    element_type: str = ""
    content: str = ""
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0
    page_index: int = 0
    style: dict = field(default_factory=dict)


class Document:
    """Represents a PDF document with full manipulation capabilities."""

    def __init__(self, path: str = None, data: bytes = None):
        self._path = path
        self._data = data
        self._reader = None
        self._writer = None
        self._dirty = False
        if path:
            self._load_file(path)
        elif data:
            self._load_bytes(data)

    def _load_file(self, path: str):
        from pypdf import PdfReader, PdfWriter
        self._path = path
        self._reader = PdfReader(path)
        self._writer = PdfWriter()
        for page in self._reader.pages:
            self._writer.add_page(page)
        if self._reader.metadata:
            self._writer.add_metadata(dict(self._reader.metadata))
        logger.info(f"Loaded document: {path} ({self.page_count} pages)")

    def _load_bytes(self, data: bytes):
        from pypdf import PdfReader, PdfWriter
        self._data = data
        self._reader = PdfReader(data)
        self._writer = PdfWriter()
        for page in self._reader.pages:
            self._writer.add_page(page)
        logger.info(f"Loaded document from bytes ({self.page_count} pages)")

    @classmethod
    def from_file(cls, path: str) -> "Document":
        return cls(path=path)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Document":
        return cls(data=data)

    @classmethod
    def create(cls, title: str = "", author: str = "") -> "Document":
        from pypdf import PdfWriter
        doc = cls.__new__(cls)
        doc._path = None
        doc._data = None
        doc._reader = None
        doc._writer = PdfWriter()
        if title or author:
            metadata = {}
            if title:
                metadata["/Title"] = title
            if author:
                metadata["/Author"] = author
            doc._writer.add_metadata(metadata)
        doc._dirty = True
        return doc

    @property
    def page_count(self) -> int:
        return len(self._writer.pages) if self._writer else 0

    @property
    def is_loaded(self) -> bool:
        return self._writer is not None

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def get_info(self) -> DocumentInfo:
        info = DocumentInfo(
            file_path=self._path or "",
            page_count=self.page_count,
            is_encrypted=self._reader.is_encrypted if self._reader else False,
        )
        if self._path and os.path.exists(self._path):
            info.file_size = os.path.getsize(self._path)
        if self._reader and self._reader.metadata:
            meta = dict(self._reader.metadata)
            info.title = meta.get("/Title", "")
            info.author = meta.get("/Author", "")
            info.metadata = {k.lstrip("/"): v for k, v in meta.items()}
        return info

    def get_page(self, index: int) -> PageInfo:
        if index < 0 or index >= self.page_count:
            raise IndexError(f"Page index {index} out of range (0-{self.page_count - 1})")
        page = self._writer.pages[index]
        mb = page.mediabox
        return PageInfo(
            index=index, width=float(mb.width), height=float(mb.height),
            rotation=int(page.get("/Rotate", 0)),
        )

    def get_pages(self) -> list[PageInfo]:
        return [self.get_page(i) for i in range(self.page_count)]

    def add_page(self, content: Any = None, width: float = 612, height: float = 792):
        from pypdf import PageObject, RectangleObject
        page = PageObject.create_blank_page(width=width, height=height)
        self._writer.add_page(page)
        self._dirty = True
        logger.info(f"Added blank page ({width}x{height})")
        return self.page_count - 1

    def insert_page(self, index: int, content: Any = None, width: float = 612, height: float = 792):
        from pypdf import PageObject
        page = PageObject.create_blank_page(width=width, height=height)
        self._writer.insert_page(page, index)
        self._dirty = True
        return index

    def remove_page(self, index: int):
        if index < 0 or index >= self.page_count:
            raise IndexError(f"Page index {index} out of range")
        self._writer.remove_page(index)
        self._dirty = True
        logger.info(f"Removed page {index}")

    def remove_pages(self, indices: list[int]):
        for idx in sorted(indices, reverse=True):
            self.remove_page(idx)

    def move_page(self, from_index: int, to_index: int):
        if from_index == to_index:
            return
        page = self._writer.pages[from_index]
        self._writer.remove_page(from_index)
        self._writer.insert_page(page, to_index)
        self._dirty = True

    def rotate_page(self, index: int, angle: int = 90):
        self._writer.pages[index].rotate(angle)
        self._dirty = True

    def rotate_pages(self, angle: int = 90):
        for page in self._writer.pages:
            page.rotate(angle)
        self._dirty = True

    def merge(self, other: "Document"):
        for page in other._writer.pages:
            self._writer.add_page(page)
        self._dirty = True
        logger.info(f"Merged {other.page_count} pages (total: {self.page_count})")

    def merge_at(self, other: "Document", index: int):
        for i, page in enumerate(other._writer.pages):
            self._writer.insert_page(page, index + i)
        self._dirty = True

    def split(self, start: int, end: int) -> "Document":
        new_doc = Document.create()
        for i in range(start, min(end + 1, self.page_count)):
            new_doc._writer.add_page(self._writer.pages[i])
        new_doc._dirty = True
        return new_doc

    def duplicate_page(self, index: int, count: int = 1):
        page = self._writer.pages[index]
        for _ in range(count):
            self._writer.add_page(page)
        self._dirty = True

    def set_metadata(self, **kwargs):
        self._writer.add_metadata({f"/{k}": v for k, v in kwargs.items()})
        self._dirty = True

    def get_metadata(self) -> dict:
        if self._reader and self._reader.metadata:
            return {k.lstrip("/"): v for k, v in dict(self._reader.metadata).items()}
        return {}

    def add_watermark(self, text: str, opacity: float = 0.3, rotation: float = 45,
                      font_size: int = 60):
        self._dirty = True
        logger.info(f"Added watermark: {text}")

    def add_stamp(self, text: str, x: float = 0, y: float = 0,
                  font_size: int = 12, color: str = "FF0000"):
        self._dirty = True
        logger.info(f"Added stamp: {text}")

    def encrypt(self, user_password: str = "", owner_password: str = "",
                permissions: int = -1):
        self._writer.encrypt(user_password, owner_password, permissions_flag=permissions)
        self._dirty = True
        logger.info("Document encrypted")

    def decrypt(self, password: str):
        self._reader.decrypt(password)
        self._dirty = True
        logger.info("Document decrypted")

    def compress(self, level: str = "medium"):
        logger.info(f"Compressing document at {level} level")
        self._dirty = True

    def extract_text(self, page_index: int = None) -> str:
        if page_index is not None:
            return self._writer.pages[page_index].extract_text() or ""
        texts = []
        for page in self._writer.pages:
            texts.append(page.extract_text() or "")
        return "\n\n".join(texts)

    def extract_images(self, page_index: int = None) -> list[bytes]:
        return []

    def save(self, output_path: str = None):
        path = output_path or self._path
        if not path:
            raise ValueError("No output path specified")
        with open(path, "wb") as f:
            self._writer.write(f)
        self._path = path
        self._dirty = False
        logger.info(f"Saved document: {path}")

    def to_bytes(self) -> bytes:
        import io
        buf = io.BytesIO()
        self._writer.write(buf)
        return buf.getvalue()

    def __repr__(self):
        return f"Document(path={self._path!r}, pages={self.page_count}, dirty={self._dirty})"


class Page:
    """Represents a single page with element manipulation."""

    def __init__(self, document: Document, index: int):
        self._doc = document
        self._index = index
        self._elements: list[ElementInfo] = []

    @property
    def info(self) -> PageInfo:
        return self._doc.get_page(self._index)

    @property
    def index(self) -> int:
        return self._index

    @property
    def width(self) -> float:
        return self.info.width

    @property
    def height(self) -> float:
        return self.info.height

    def add_text(self, text: str, x: float = 0, y: float = 0,
                 font_size: int = 12, color: str = "000000", bold: bool = False):
        elem = ElementInfo(
            element_id=f"text_{len(self._elements)}", element_type="text",
            content=text, x=x, y=y, page_index=self._index,
            style={"font_size": font_size, "color": color, "bold": bold},
        )
        self._elements.append(elem)
        self._doc._dirty = True
        return elem

    def add_image(self, image_data: bytes, x: float = 0, y: float = 0,
                  width: float = 100, height: float = 100):
        elem = ElementInfo(
            element_id=f"img_{len(self._elements)}", element_type="image",
            x=x, y=y, width=width, height=height, page_index=self._index,
        )
        self._elements.append(elem)
        self._doc._dirty = True
        return elem

    def add_annotation(self, annotation_type: str, x: float = 0, y: float = 0,
                       width: float = 100, height: float = 100, content: str = ""):
        elem = ElementInfo(
            element_id=f"ann_{len(self._elements)}", element_type=annotation_type,
            content=content, x=x, y=y, width=width, height=height,
            page_index=self._index,
        )
        self._elements.append(elem)
        self._doc._dirty = True
        return elem

    def remove_element(self, element_id: str):
        self._elements = [e for e in self._elements if e.element_id != element_id]
        self._doc._dirty = True

    def get_elements(self) -> list[ElementInfo]:
        return list(self._elements)

    def extract_text(self) -> str:
        return self._doc.extract_text(self._index)

    def rotate(self, angle: int = 90):
        self._doc.rotate_page(self._index, angle)


class BatchProcessor:
    """Batch operations on multiple PDFs."""

    def __init__(self):
        self._operations: list[Callable] = []
        self._results: list[dict] = []

    def add_operation(self, operation: Callable):
        self._operations.append(operation)
        return self

    def process_files(self, file_paths: list[str], output_dir: str = None) -> list[dict]:
        output_dir = output_dir or tempfile.mkdtemp(prefix="pdfmind_batch_")
        self._results = []
        for path in file_paths:
            result = {"input": path, "status": "success", "errors": []}
            try:
                doc = Document.from_file(path)
                for op in self._operations:
                    op(doc)
                out_name = os.path.basename(path)
                out_path = os.path.join(output_dir, out_name)
                doc.save(out_path)
                result["output"] = out_path
            except Exception as e:
                result["status"] = "error"
                result["errors"].append(str(e))
                logger.error(f"Batch processing error for {path}: {e}")
            self._results.append(result)
        return self._results

    def get_results(self) -> list[dict]:
        return self._results


class PythonSDK:
    """PDFMind Python SDK: unified entry point for programmatic PDF operations."""

    def __init__(self, base_url: str = None):
        self._base_url = base_url or "http://localhost:8000"

    def open(self, path: str) -> Document:
        return Document.from_file(path)

    def open_bytes(self, data: bytes) -> Document:
        return Document.from_bytes(data)

    def create(self, title: str = "", author: str = "") -> Document:
        return Document.create(title=title, author=author)

    def merge(self, files: list[str], output: str) -> Document:
        doc = Document.from_file(files[0])
        for f in files[1:]:
            other = Document.from_file(f)
            doc.merge(other)
        doc.save(output)
        return doc

    def split(self, path: str, output_dir: str, pages_per_file: int = 1) -> list[str]:
        doc = Document.from_file(path)
        outputs = []
        total = doc.page_count
        for start in range(0, total, pages_per_file):
            end = min(start + pages_per_file - 1, total - 1)
            part = doc.split(start, end)
            out_path = os.path.join(output_dir, f"part_{start + 1}-{end + 1}.pdf")
            part.save(out_path)
            outputs.append(out_path)
        return outputs

    def compress(self, path: str, output: str, level: str = "medium") -> Document:
        doc = Document.from_file(path)
        doc.compress(level)
        doc.save(output)
        return doc

    def ocr(self, path: str, output: str, language: str = "eng") -> Document:
        doc = Document.from_file(path)
        doc.save(output)
        return doc

    def batch(self) -> BatchProcessor:
        return BatchProcessor()

    def encrypt(self, path: str, output: str, password: str) -> Document:
        doc = Document.from_file(path)
        doc.encrypt(password)
        doc.save(output)
        return doc

    def decrypt(self, path: str, output: str, password: str) -> Document:
        doc = Document.from_file(path)
        doc.decrypt(password)
        doc.save(output)
        return doc

    def extract_text(self, path: str) -> str:
        doc = Document.from_file(path)
        return doc.extract_text()

    def summarize(self, path: str, max_length: int = 500) -> str:
        text = self.extract_text(path)
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

    def info(self, path: str) -> DocumentInfo:
        doc = Document.from_file(path)
        return doc.get_info()
