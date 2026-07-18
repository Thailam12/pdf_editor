"""PDF split operations.

Split documents by ranges, bookmarks, file size, or fixed counts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import fitz  # PyMuPDF


def split_by_ranges(
    source: Union[str, Path, fitz.Document],
    ranges: Sequence[Tuple[int, int]],
    output_dir: Union[str, Path],
    base_name: str = "split",
) -> List[Path]:
    """Split a PDF into separate files by page ranges.

    Args:
        source: Input PDF.
        ranges: Sequence of ``(start, end)`` inclusive 0-based page indices.
        output_dir: Directory to write output files.
        base_name: Base filename prefix.

    Returns:
        List of paths to the created files.
    """
    doc = _open(source)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []
    for idx, (start, end) in enumerate(ranges):
        start = max(0, start)
        end = min(end, len(doc) - 1)
        if start > end:
            continue
        out = fitz.open()
        out.insert_pdf(doc, from_page=start, to_page=end)
        path = out_dir / f"{base_name}_{idx + 1}.pdf"
        out.save(str(path))
        out.close()
        created.append(path)
    return created


def split_by_bookmarks(
    source: Union[str, Path, fitz.Document],
    output_dir: Union[str, Path],
    base_name: str = "chapter",
    level: int = 1,
) -> List[Path]:
    """Split a PDF at top-level bookmark boundaries."""
    doc = _open(source)
    toc = doc.get_toc(simple=True)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    chapter_starts = [entry[2] - 1 for entry in toc if entry[0] <= level]
    if not chapter_starts:
        return []

    boundaries = chapter_starts + [len(doc)]
    created: List[Path] = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1] - 1
        title = toc[i][1] if i < len(toc) else f"section_{i + 1}"
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:80]
        out = fitz.open()
        out.insert_pdf(doc, from_page=start, to_page=end)
        path = out_dir / f"{base_name}_{i + 1}_{safe}.pdf"
        out.save(str(path))
        out.close()
        created.append(path)
    return created


def split_by_size(
    source: Union[str, Path, fitz.Document],
    output_dir: Union[str, Path],
    max_bytes: int = 10 * 1024 * 1024,
    base_name: str = "chunk",
) -> List[Path]:
    """Split a PDF so no output file exceeds *max_bytes*.

    This is a heuristic: pages are grouped until the accumulated
    uncompressed content exceeds the threshold.
    """
    doc = _open(source)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []
    chunk = fitz.open()
    chunk_bytes = 0
    chunk_idx = 0

    for page_num in range(len(doc)):
        chunk.insert_pdf(doc, from_page=page_num, to_page=page_num)
        page_bytes = doc[page_num].get_contents()
        size_est = sum(len(c) if isinstance(c, (bytes,)) else os.path.getsize(str(c))
                        if not isinstance(c, bytes) else len(c)
                        for c in doc[page_num].get_contents()) if False else len(doc.tobytes()) // max(1, len(doc))

        if chunk_bytes > max_bytes and len(chunk) > 1:
            chunk.delete_page(-1)
            path = out_dir / f"{base_name}_{chunk_idx + 1}.pdf"
            chunk.save(str(path))
            chunk.close()
            created.append(path)
            chunk_idx += 1
            chunk = fitz.open()
            chunk.insert_pdf(doc, from_page=page_num, to_page=page_num)
            chunk_bytes = 0
        chunk_bytes += size_est

    if len(chunk) > 0:
        path = out_dir / f"{base_name}_{chunk_idx + 1}.pdf"
        chunk.save(str(path))
        chunk.close()
        created.append(path)
    else:
        chunk.close()
    return created


def split_every_n(
    source: Union[str, Path, fitz.Document],
    n: int,
    output_dir: Union[str, Path],
    base_name: str = "part",
) -> List[Path]:
    """Split a PDF into chunks of *n* pages each."""
    doc = _open(source)
    total = len(doc)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []
    for start in range(0, total, n):
        end = min(start + n - 1, total - 1)
        out = fitz.open()
        out.insert_pdf(doc, from_page=start, to_page=end)
        part_num = start // n + 1
        path = out_dir / f"{base_name}_{part_num}.pdf"
        out.save(str(path))
        out.close()
        created.append(path)
    return created


def extract_pages(
    source: Union[str, Path, fitz.Document],
    pages: Sequence[int],
    output_path: Union[str, Path],
) -> Path:
    """Extract specific pages to a new PDF.

    Args:
        source: Input PDF.
        pages: 0-based page indices to extract.
        output_path: Destination file.
    """
    doc = _open(source)
    out = fitz.open()
    for p in pages:
        if 0 <= p < len(doc):
            out.insert_pdf(doc, from_page=p, to_page=p)
    out.save(str(output_path))
    out.close()
    return Path(output_path)


def _open(src: Union[str, Path, fitz.Document]) -> fitz.Document:
    if isinstance(src, fitz.Document):
        return src
    return fitz.open(str(src))
