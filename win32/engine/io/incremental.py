"""Incremental save manager.

Tracks changes to a PDF document and writes only modified objects
using PyMuPDF's incremental save capability, preserving revision history.
"""

from __future__ import annotations

import copy
import hashlib
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import fitz  # PyMuPDF


class ChangeType(Enum):
    PAGE_MODIFIED = auto()
    PAGE_ADDED = auto()
    PAGE_DELETED = auto()
    ANNOTATION_MODIFIED = auto()
    ANNOTATION_ADDED = auto()
    ANNOTATION_DELETED = auto()
    METADATA_MODIFIED = auto()
    TOC_MODIFIED = auto()
    FORM_MODIFIED = auto()
    IMAGE_MODIFIED = auto()


@dataclass
class ChangeRecord:
    """A single tracked change."""
    change_type: ChangeType
    page_index: int = -1
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    data_snapshot: Optional[Dict[str, Any]] = None


class IncrementalSaveManager:
    """Tracks changes and performs incremental saves.

    PyMuPDF supports appending new objects at the end of an existing
    PDF file, avoiding the need to rewrite the whole document.
    This manager keeps a log of what changed and provides methods
    to persist only those changes.
    """

    def __init__(self, source_path: Union[str, Path]) -> None:
        self._source_path = Path(source_path)
        if not self._source_path.exists():
            raise FileNotFoundError(f"Source PDF not found: {self._source_path}")
        self._doc = fitz.open(str(self._source_path))
        self._base_path = Path(str(self._source_path))
        self._changes: List[ChangeRecord] = []
        self._modified_pages: Set[int] = set()
        self._added_pages: Set[int] = set()
        self._deleted_pages: Set[int] = set()
        self._metadata_dirty = False
        self._toc_dirty = False
        self._initial_xref_count = self._doc.xref_length()
        self._snapshots: Dict[int, bytes] = {}
        self._revision_count = 0

    @property
    def has_unsaved_changes(self) -> bool:
        return len(self._changes) > 0

    @property
    def change_count(self) -> int:
        return len(self._changes)

    @property
    def revision_count(self) -> int:
        return self._revision_count

    def snapshot_page(self, page_index: int) -> None:
        """Save a byte snapshot of a page for undo support."""
        page = self._doc[page_index]
        self._snapshots[page_index] = page.read_contents()

    def get_changes(self) -> List[ChangeRecord]:
        return list(self._changes)

    def get_changes_for_page(self, page_index: int) -> List[ChangeRecord]:
        return [c for c in self._changes if c.page_index == page_index]

    def mark_page_modified(self, page_index: int, description: str = "") -> None:
        self._changes.append(ChangeRecord(
            change_type=ChangeType.PAGE_MODIFIED,
            page_index=page_index,
            description=description or f"Page {page_index} modified",
        ))
        self._modified_pages.add(page_index)

    def mark_page_added(self, page_index: int, description: str = "") -> None:
        self._changes.append(ChangeRecord(
            change_type=ChangeType.PAGE_ADDED,
            page_index=page_index,
            description=description or f"Page {page_index} added",
        ))
        self._added_pages.add(page_index)

    def mark_page_deleted(self, page_index: int, description: str = "") -> None:
        self._changes.append(ChangeRecord(
            change_type=ChangeType.PAGE_DELETED,
            page_index=page_index,
            description=description or f"Page {page_index} deleted",
        ))
        self._deleted_pages.add(page_index)

    def mark_metadata_modified(self) -> None:
        self._changes.append(ChangeRecord(
            change_type=ChangeType.METADATA_MODIFIED,
            description="Document metadata modified",
        ))
        self._metadata_dirty = True

    def mark_toc_modified(self) -> None:
        self._changes.append(ChangeRecord(
            change_type=ChangeType.TOC_MODIFIED,
            description="Table of contents modified",
        ))
        self._toc_dirty = True

    def mark_annotation_changed(
        self, page_index: int, annot_name: str, change: ChangeType
    ) -> None:
        self._changes.append(ChangeRecord(
            change_type=change,
            page_index=page_index,
            description=f"Annotation '{annot_name}' changed on page {page_index}",
        ))

    def save_incremental(self, output_path: Optional[Union[str, Path]] = None) -> Path:
        """Save only changed objects by appending to the original file.

        Falls back to a full save if incremental is not possible.
        """
        target = Path(output_path) if output_path else self._base_path
        can_incremental = (
            not self._added_pages
            and not self._deleted_pages
            and str(target) == str(self._base_path)
        )
        try:
            if can_incremental:
                self._doc.save(
                    str(target),
                    incremental=True,
                    deflate=True,
                    garbage=0,
                )
            else:
                self._doc.save(
                    str(target),
                    garbage=4,
                    deflate=True,
                    deflate_level=6,
                )
                self._base_path = Path(str(target))
        except Exception:
            self._doc.save(
                str(target),
                garbage=4,
                deflate=True,
                incremental=False,
            )
            self._base_path = Path(str(target))

        self._revision_count += 1
        self._changes.clear()
        self._modified_pages.clear()
        self._added_pages.clear()
        self._deleted_pages.clear()
        self._metadata_dirty = False
        self._toc_dirty = False
        self._initial_xref_count = self._doc.xref_length()
        return target

    def get_revision_info(self) -> List[Dict[str, Any]]:
        """Return information about each saved revision."""
        info = []
        xref_count = self._doc.xref_length()
        info.append({
            "revision": 0,
            "xref_count": self._initial_xref_count,
            "description": "Original document",
        })
        if self._revision_count > 0:
            info.append({
                "revision": self._revision_count,
                "xref_count": xref_count,
                "description": f"Revision {self._revision_count}",
            })
        return info

    def compute_file_hash(self) -> str:
        data = self._doc.tobytes()
        return hashlib.sha256(data).hexdigest()

    def get_modified_page_indices(self) -> Set[int]:
        return set(self._modified_pages)

    def close(self) -> None:
        if self._doc:
            self._doc.close()

    def __enter__(self) -> IncrementalSaveManager:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
