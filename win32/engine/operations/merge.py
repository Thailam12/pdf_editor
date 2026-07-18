"""PDF merge operations.

Combine multiple PDFs, insert pages, merge with page ranges, and
interleave pages from various sources.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import fitz  # PyMuPDF


def merge_pdfs(
    sources: Sequence[Union[str, Path, fitz.Document]],
    output_path: Union[str, Path],
    bookmarks: bool = True,
    page_size_strategy: str = "first",
) -> fitz.Document:
    """Merge multiple PDFs into a single document.

    Args:
        sources: Paths or open Document objects to merge.
        output_path: Destination file path.
        bookmarks: Preserve source bookmarks as top-level entries.
        page_size_strategy: ``"first"`` uses the first source's page size,
            ``"largest"`` uses the largest page across all sources.
    """
    dest = fitz.open()
    for idx, src in enumerate(sources):
        doc = _open_source(src)
        try:
            if bookmarks:
                toc_level0 = doc.get_toc(simple=False)
                first_page = len(dest)
                for entry in toc_level0:
                    level, title, page = entry[:3]
                    dest.set_toc([[level, title, page + first_page]])
            for page_num in range(len(doc)):
                dest.insert_pdf(doc, from_page=page_num, to_page=page_num)
        finally:
            if isinstance(src, (str, Path)):
                doc.close()
    dest.save(str(output_path))
    dest.close()
    return fitz.open(str(output_path))


def insert_pages(
    target: Union[str, Path, fitz.Document],
    source: Union[str, Path, fitz.Document],
    position: int = 0,
    page_range: Optional[Tuple[int, int]] = None,
) -> fitz.Document:
    """Insert pages from *source* into *target* at the given position."""
    target_doc = _open_source(target)
    source_doc = _open_source(source)
    try:
        start = page_range[0] if page_range else 0
        end = page_range[1] if page_range else len(source_doc) - 1
        start = max(0, start)
        end = min(end, len(source_doc) - 1)
        position = max(0, min(position, len(target_doc)))
        target_doc.insert_pdf(source_doc, from_page=start, to_page=end, start_at=position)
    finally:
        if isinstance(source, (str, Path)):
            source_doc.close()
    return target_doc


def merge_with_ranges(
    sources: Sequence[Tuple[Union[str, Path, fitz.Document], Tuple[int, int]]],
    output_path: Union[str, Path],
) -> fitz.Document:
    """Merge selected page ranges from multiple sources.

    Each entry in *sources* is ``(source, (start, end))``.
    """
    dest = fitz.open()
    for src, (start, end) in sources:
        doc = _open_source(src)
        try:
            start = max(0, start)
            end = min(end, len(doc) - 1)
            dest.insert_pdf(doc, from_page=start, to_page=end)
        finally:
            if isinstance(src, (str, Path)):
                doc.close()
    dest.save(str(output_path))
    dest.close()
    return fitz.open(str(output_path))


def interleave_pages(
    sources: Sequence[Union[str, Path, fitz.Document]],
    output_path: Union[str, Path],
) -> fitz.Document:
    """Interleave pages from multiple sources round-robin style.

    Pages are taken in order from each source, cycling until all sources
    are exhausted.
    """
    docs = [_open_source(s) for s in sources]
    src_paths = [s for s, d in zip(sources, docs) if isinstance(s, (str, Path))]
    dest = fitz.open()
    try:
        max_len = max(len(d) for d in docs) if docs else 0
        for page_idx in range(max_len):
            for doc in docs:
                if page_idx < len(doc):
                    dest.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
    finally:
        for doc, src in zip(docs, sources):
            if isinstance(src, (str, Path)):
                doc.close()
    dest.save(str(output_path))
    dest.close()
    return fitz.open(str(output_path))


def _open_source(src: Union[str, Path, fitz.Document]) -> fitz.Document:
    if isinstance(src, fitz.Document):
        return src
    return fitz.open(str(src))
