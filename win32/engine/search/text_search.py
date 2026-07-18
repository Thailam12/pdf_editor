"""Full-text search engine for PDF documents.

Extracts text with positional data and supports exact, case-insensitive,
whole-word, and multi-page search with highlight regions and caching.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class SearchOptions:
    """Configuration for a text search operation."""
    case_sensitive: bool = False
    whole_word: bool = False
    use_regex: bool = False
    max_results: int = 0  # 0 = unlimited
    page_numbers: Optional[List[int]] = None  # None = all pages
    context_chars: int = 0  # characters of context around match
    find_all: bool = True  # find all matches or stop at first

    @property
    def flags(self) -> int:
        f = 0
        if not self.case_sensitive:
            f |= re.IGNORECASE
        if self.whole_word:
            f |= re.WORD
        return f


@dataclass
class SearchResult:
    """A single search match with positional information."""
    text: str
    page_number: int
    bbox: Tuple[float, float, float, float]
    match_start: int
    match_end: int
    context_before: str = ""
    context_after: str = ""
    confidence: float = 1.0
    block_number: int = 0
    line_number: int = 0
    word_number: int = 0

    @property
    def match_length(self) -> int:
        return self.match_end - self.match_start

    @property
    def center(self) -> Tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2,
        )

    @property
    def full_context(self) -> str:
        parts = []
        if self.context_before:
            parts.append(self.context_before)
        parts.append(self.text)
        if self.context_after:
            parts.append(self.context_after)
        return "".join(parts)

    def to_highlight_rect(self) -> Dict[str, Any]:
        return {
            "x0": self.bbox[0],
            "y0": self.bbox[1],
            "x1": self.bbox[2],
            "y1": self.bbox[3],
            "page": self.page_number,
        }


@dataclass
class SearchIndex:
    """Cached text index for fast repeated searches."""
    doc_id: str
    page_data: List[Dict[str, Any]]
    full_text: str
    page_offsets: List[Tuple[int, int]]
    total_chars: int
    timestamp: float = 0.0

    @property
    def page_count(self) -> int:
        return len(self.page_data)


class SearchIndexBuilder:
    """Builds and manages text search indexes from PDF documents."""

    def __init__(self):
        self._indexes: Dict[str, SearchIndex] = {}
        self._lock = threading.Lock()

    def build_index(self, doc: fitz.Document, doc_id: Optional[str] = None) -> SearchIndex:
        doc_id = doc_id or self._doc_id(doc)

        with self._lock:
            if doc_id in self._indexes:
                return self._indexes[doc_id]

        page_data: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []
        page_offsets: List[Tuple[int, int]] = []
        running_offset = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            words = page.get_text("words")
            blocks = page.get_text("dict").get("blocks", [])

            page_text = page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            page_start = running_offset
            page_end = running_offset + len(page_text)
            page_offsets.append((page_start, page_end))
            full_text_parts.append(page_text)
            running_offset = page_end

            page_entry = {
                "page_number": page_num,
                "text": page_text,
                "words": [
                    {
                        "text": w[4],
                        "bbox": (w[0], w[1], w[2], w[3]),
                        "block_number": w[5],
                        "line_number": w[6],
                        "word_number": w[7],
                    }
                    for w in words
                ],
                "char_positions": self._extract_char_positions(page),
                "text_offset": page_start,
            }
            page_data.append(page_entry)

        full_text = "".join(full_text_parts)
        index = SearchIndex(
            doc_id=doc_id,
            page_data=page_data,
            full_text=full_text,
            page_offsets=page_offsets,
            total_chars=len(full_text),
            timestamp=time.time(),
        )

        with self._lock:
            self._indexes[doc_id] = index

        return index

    def get_index(self, doc_id: str) -> Optional[SearchIndex]:
        with self._lock:
            return self._indexes.get(doc_id)

    def invalidate(self, doc_id: Optional[str] = None) -> None:
        with self._lock:
            if doc_id:
                self._indexes.pop(doc_id, None)
            else:
                self._indexes.clear()

    @staticmethod
    def _extract_char_positions(page: fitz.Page) -> List[Dict[str, Any]]:
        text_dict = page.get_text("rawdict")
        positions: List[Dict[str, Any]] = []
        global_offset = 0

        for block in text_dict.get("blocks", []):
            if block["type"] != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    origin = span.get("origin", (0, 0))
                    bbox = span.get("bbox", (0, 0, 0, 0))
                    font_size = span.get("size", 12.0)
                    span_width = bbox[2] - bbox[0]
                    char_count = len(text)
                    avg_width = span_width / char_count if char_count > 0 else 0

                    for i, ch in enumerate(text):
                        cx = origin[0] + i * avg_width
                        positions.append({
                            "char": ch,
                            "index": global_offset,
                            "x": cx,
                            "y": origin[1],
                            "width": avg_width,
                            "height": font_size,
                            "bbox": (
                                cx,
                                origin[1] - font_size,
                                cx + avg_width,
                                origin[1],
                            ),
                            "font_size": font_size,
                        })
                        global_offset += 1

        return positions

    @staticmethod
    def _doc_id(doc: fitz.Document) -> str:
        try:
            return doc.name or str(id(doc))
        except Exception:
            return str(id(doc))


class TextSearchEngine:
    """Full-text search engine for PDF documents.

    Extracts text with word-level positions and provides fast searching
    with an optional cached index for repeated queries.
    """

    def __init__(self):
        self._index_builder = SearchIndexBuilder()
        self._highlight_cache: Dict[str, List[Tuple[float, float, float, float]]] = {}

    def search(
        self,
        doc: fitz.Document,
        query: str,
        options: Optional[SearchOptions] = None,
    ) -> List[SearchResult]:
        if not query:
            return []

        options = options or SearchOptions()
        index = self._index_builder.build_index(doc)
        results: List[SearchResult] = []

        if options.use_regex:
            results = self._regex_search(index, query, options)
        elif options.whole_word:
            results = self._whole_word_search(index, query, options)
        else:
            results = self._simple_search(index, query, options)

        if options.context_chars > 0:
            results = self._add_context(index, results, options.context_chars)

        if options.max_results > 0:
            results = results[: options.max_results]

        return results

    def search_single_page(
        self,
        page: fitz.Page,
        query: str,
        case_sensitive: bool = False,
    ) -> List[SearchResult]:
        page_num = page.number
        words = page.get_text("words")
        text = page.get_text("text")
        results: List[SearchResult] = []

        try:
            hits = page.search_for(
                query,
                quads=False,
            )
        except Exception:
            hits = []

        if hits:
            for rect in hits:
                match_text = self._extract_text_in_rect(page, rect)
                results.append(SearchResult(
                    text=match_text or query,
                    page_number=page_num,
                    bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                    match_start=0,
                    match_end=len(match_text or query),
                ))
            return results

        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)

        for match in pattern.finditer(text):
            start = match.start()
            end = match.end()
            bbox = self._estimate_bbox_from_text(text, words, start, end)
            if bbox:
                results.append(SearchResult(
                    text=match.group(),
                    page_number=page_num,
                    bbox=bbox,
                    match_start=start,
                    match_end=end,
                ))

        return results

    def highlight_results(
        self,
        doc: fitz.Document,
        results: List[SearchResult],
        color: Tuple[float, float, float] = (1.0, 1.0, 0.0),
        opacity: float = 0.4,
    ) -> Dict[int, List[Dict[str, Any]]]:
        highlights: Dict[int, List[Dict[str, Any]]] = {}

        for result in results:
            page_num = result.page_number
            if page_num not in highlights:
                highlights[page_num] = []

            highlights[page_num].append({
                "rect": {
                    "x0": result.bbox[0],
                    "y0": result.bbox[1],
                    "x1": result.bbox[2],
                    "y1": result.bbox[3],
                },
                "text": result.text,
                "color": color,
                "opacity": opacity,
            })

        return highlights

    def get_match_statistics(
        self, doc: fitz.Document, query: str, options: Optional[SearchOptions] = None
    ) -> Dict[str, Any]:
        options = options or SearchOptions()
        options.find_all = True
        options.max_results = 0
        start_time = time.time()
        results = self.search(doc, query, options)
        elapsed = time.time() - start_time

        pages_with_matches: Set[int] = set(r.page_number for r in results)
        return {
            "query": query,
            "total_matches": len(results),
            "pages_with_matches": sorted(pages_with_matches),
            "page_count": len(pages_with_matches),
            "search_time_ms": elapsed * 1000,
            "case_sensitive": options.case_sensitive,
            "whole_word": options.whole_word,
        }

    def invalidate_index(self, doc_id: Optional[str] = None) -> None:
        self._index_builder.invalidate(doc_id)

    def _simple_search(
        self, index: SearchIndex, query: str, options: SearchOptions
    ) -> List[SearchResult]:
        results: List[SearchResult] = []
        flags = 0 if options.case_sensitive else re.IGNORECASE
        query_lower = query.lower() if not options.case_sensitive else query

        for page_entry in index.page_data:
            if options.page_numbers and page_entry["page_number"] not in options.page_numbers:
                continue

            page_text = page_entry["text"]
            text_lower = page_text.lower() if not options.case_sensitive else page_text
            offset = 0

            while True:
                pos = text_lower.find(query_lower, offset)
                if pos == -1:
                    break

                bbox = self._bbox_from_char_positions(
                    page_entry["char_positions"],
                    page_entry["text_offset"] + pos,
                    page_entry["text_offset"] + pos + len(query),
                    pos,
                    pos + len(query),
                    page_text,
                )

                result = SearchResult(
                    text=page_text[pos: pos + len(query)],
                    page_number=page_entry["page_number"],
                    bbox=bbox or (0.0, 0.0, 0.0, 0.0),
                    match_start=pos,
                    match_end=pos + len(query),
                )
                results.append(result)
                offset = pos + 1

                if not options.find_all:
                    return results

        return results

    def _whole_word_search(
        self, index: SearchIndex, query: str, options: SearchOptions
    ) -> List[SearchResult]:
        results: List[SearchResult] = []
        flags = re.IGNORECASE if not options.case_sensitive else 0
        pattern = re.compile(r'\b' + re.escape(query) + r'\b', flags)

        for page_entry in index.page_data:
            if options.page_numbers and page_entry["page_number"] not in options.page_numbers:
                continue

            page_text = page_entry["text"]
            for match in pattern.finditer(page_text):
                pos = match.start()
                end = match.end()
                bbox = self._bbox_from_char_positions(
                    page_entry["char_positions"],
                    page_entry["text_offset"] + pos,
                    page_entry["text_offset"] + end,
                    pos,
                    end,
                    page_text,
                )
                results.append(SearchResult(
                    text=match.group(),
                    page_number=page_entry["page_number"],
                    bbox=bbox or (0.0, 0.0, 0.0, 0.0),
                    match_start=pos,
                    match_end=end,
                ))

                if not options.find_all:
                    return results

        return results

    def _regex_search(
        self, index: SearchIndex, query: str, options: SearchOptions
    ) -> List[SearchResult]:
        results: List[SearchResult] = []
        flags = 0 if options.case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query, flags)
        except re.error as e:
            logger.warning("Invalid regex pattern '%s': %s", query, e)
            return results

        for page_entry in index.page_data:
            if options.page_numbers and page_entry["page_number"] not in options.page_numbers:
                continue

            page_text = page_entry["text"]
            for match in pattern.finditer(page_text):
                pos = match.start()
                end = match.end()
                bbox = self._bbox_from_char_positions(
                    page_entry["char_positions"],
                    page_entry["text_offset"] + pos,
                    page_entry["text_offset"] + end,
                    pos,
                    end,
                    page_text,
                )
                results.append(SearchResult(
                    text=match.group(),
                    page_number=page_entry["page_number"],
                    bbox=bbox or (0.0, 0.0, 0.0, 0.0),
                    match_start=pos,
                    match_end=end,
                ))

                if not options.find_all:
                    return results

        return results

    def _add_context(
        self,
        index: SearchIndex,
        results: List[SearchResult],
        context_chars: int,
    ) -> List[SearchResult]:
        for result in results:
            page_data = None
            for pd in index.page_data:
                if pd["page_number"] == result.page_number:
                    page_data = pd
                    break

            if page_data is None:
                continue

            text = page_data["text"]
            start = max(0, result.match_start - context_chars)
            end = min(len(text), result.match_end + context_chars)
            result.context_before = text[start: result.match_start]
            result.context_after = text[result.match_end: end]

        return results

    def _bbox_from_char_positions(
        self,
        char_positions: List[Dict[str, Any]],
        global_start: int,
        global_end: int,
        local_start: int,
        local_end: int,
        page_text: str,
    ) -> Optional[Tuple[float, float, float, float]]:
        if not char_positions:
            return None

        x_min = float("inf")
        y_min = float("inf")
        x_max = float("-inf")
        y_max = float("-inf")
        found = False

        for cp in char_positions:
            idx = cp.get("index", -1)
            if idx < local_start or idx >= local_end:
                continue
            found = True
            bbox = cp.get("bbox", (0, 0, 0, 0))
            x_min = min(x_min, bbox[0])
            y_min = min(y_min, bbox[1])
            x_max = max(x_max, bbox[2])
            y_max = max(y_max, bbox[3])

        if found and x_min < float("inf"):
            return (x_min, y_min, x_max, y_max)

        match_len = local_end - local_start
        est_x = local_start * 8.0
        est_w = match_len * 8.0
        return (est_x, 0.0, est_x + est_w, 12.0)

    def _estimate_bbox_from_text(
        self, text: str, words: list, start: int, end: int
    ) -> Optional[Tuple[float, float, float, float]]:
        for w in words:
            w_text = w[4]
            w_bbox = (w[0], w[1], w[2], w[3])
            w_start = text.find(w_text)
            if w_start == -1:
                continue
            w_end = w_start + len(w_text)
            if start >= w_start and end <= w_end:
                ratio_start = (start - w_start) / max(len(w_text), 1)
                ratio_end = (end - w_start) / max(len(w_text), 1)
                x0 = w_bbox[0] + ratio_start * (w_bbox[2] - w_bbox[0])
                x1 = w_bbox[0] + ratio_end * (w_bbox[2] - w_bbox[0])
                return (x0, w_bbox[1], x1, w_bbox[3])

        return None

    @staticmethod
    def _extract_text_in_rect(page: fitz.Page, rect: fitz.Rect) -> str:
        try:
            text_dict = page.get_text("dict", clip=rect)
            parts = []
            for block in text_dict.get("blocks", []):
                if block["type"] != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        parts.append(span.get("text", ""))
            return " ".join(parts)
        except Exception:
            return ""
