"""Page reordering operations.

Move, reverse, duplicate, and sort pages within a PDF document.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Union

import fitz  # PyMuPDF


def move_pages(
    doc: fitz.Document,
    from_indices: Sequence[int],
    to_index: int,
) -> None:
    """Move pages to a new position in the document.

    Pages are relocated preserving their relative order.
    """
    valid = [i for i in from_indices if 0 <= i < len(doc)]
    if not valid:
        return
    to_index = max(0, min(to_index, len(doc) - 1))
    doc.select(_compute_new_order(len(doc), valid, to_index))


def reverse_order(
    doc: fitz.Document,
    page_range: Optional[tuple] = None,
) -> None:
    """Reverse the page order, optionally within a range."""
    total = len(doc)
    if page_range:
        start, end = max(0, page_range[0]), min(total - 1, page_range[1])
        pages = list(range(total))
        sub = pages[start:end + 1]
        sub.reverse()
        pages[start:end + 1] = sub
    else:
        pages = list(range(total - 1, -1, -1))
    doc.select(pages)


def duplicate_pages(
    doc: fitz.Document,
    page_indices: Sequence[int],
    copies: int = 1,
    position: Optional[int] = None,
) -> None:
    """Duplicate the given pages *copies* times.

    If *position* is specified the duplicates are inserted there;
    otherwise they follow the original page.
    """
    total = len(doc)
    new_order: List[int] = []
    insertion_map: Dict[int, int] = {}
    for idx in page_indices:
        if 0 <= idx < total:
            insertion_map[idx] = copies
    insert_at = position if position is not None else -1
    for i in range(total):
        if insert_at == i:
            for idx in page_indices:
                if 0 <= idx < total:
                    for _ in range(copies):
                        new_order.append(idx)
        new_order.append(i)
    if insert_at == -1 or insert_at >= total:
        for idx in page_indices:
            if 0 <= idx < total:
                for _ in range(copies):
                    new_order.append(idx)
    doc.select(new_order)


def sort_by_metadata(
    doc: fitz.Document,
    key: str = "title",
    descending: bool = False,
) -> None:
    """Sort pages by document metadata.

    Currently supports sorting by page label or bookmark title
    associated with each page.
    """
    toc = doc.get_toc(simple=True)
    page_titles: Dict[int, str] = {}
    for entry in toc:
        if entry[0] == 1:
            page_titles[entry[2] - 1] = entry[1]

    if key == "title":
        order = sorted(
            range(len(doc)),
            key=lambda i: page_titles.get(i, f"page_{i:04d}"),
            reverse=descending,
        )
    elif key == "size":
        order = sorted(
            range(len(doc)),
            key=lambda i: doc[i].rect.width * doc[i].rect.height,
            reverse=descending,
        )
    elif key == "rotation":
        order = sorted(
            range(len(doc)),
            key=lambda i: doc[i].rotation,
            reverse=descending,
        )
    else:
        order = list(range(len(doc)))
    doc.select(order)


def _compute_new_order(
    total: int, moving: List[int], to: int
) -> List[int]:
    """Build the new page order after moving pages."""
    order = [i for i in range(total) if i not in moving]
    to = min(to, len(order))
    for i, m in enumerate(moving):
        order.insert(to + i, m)
    return order
