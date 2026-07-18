"""Advanced regex-based search engine for PDF documents.

Extends the base text search with full Python regex support, named groups,
multi-line matching, context extraction, and match statistics.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import fitz  # PyMuPDF

from engine.search.text_search import SearchIndex, SearchIndexBuilder, SearchResult

logger = logging.getLogger(__name__)


@dataclass
class RegexMatch:
    """A single regex match with group information."""
    text: str
    page_number: int
    bbox: Tuple[float, float, float, float]
    start: int
    end: int
    group_name: Optional[str] = None
    group_index: int = 0
    groups: Dict[str, str] = field(default_factory=dict)
    named_groups: Dict[str, Tuple[str, int, int]] = field(default_factory=dict)
    span: Tuple[int, int] = (0, 0)

    @property
    def match_length(self) -> int:
        return self.end - self.start

    @property
    def center(self) -> Tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2,
        )

    def to_highlight_rect(self) -> Dict[str, Any]:
        return {
            "x0": self.bbox[0],
            "y0": self.bbox[1],
            "x1": self.bbox[2],
            "y1": self.bbox[3],
            "page": self.page_number,
        }


@dataclass
class MatchStatistics:
    """Aggregate statistics for a regex search operation."""
    total_matches: int = 0
    total_pages_with_matches: int = 0
    matches_per_page: Dict[int, int] = field(default_factory=dict)
    group_stats: Dict[str, int] = field(default_factory=dict)
    search_time_ms: float = 0.0
    pattern_compile_time_ms: float = 0.0
    pattern: str = ""
    flags: int = 0
    is_valid: bool = True
    error_message: str = ""

    @property
    def average_matches_per_page(self) -> float:
        if self.total_pages_with_matches == 0:
            return 0.0
        return self.total_matches / self.total_pages_with_matches


@dataclass
class ContextLine:
    """A line of text with position context for search results."""
    text: str
    line_number: int
    char_offset: int
    is_match: bool = False
    match_group: Optional[str] = None


@dataclass
class RegexSearchResult:
    """Complete result from a regex search operation."""
    matches: List[RegexMatch]
    statistics: MatchStatistics
    context_lines: List[ContextLine] = field(default_factory=list)

    @property
    def total_matches(self) -> int:
        return len(self.matches)

    @property
    def has_matches(self) -> bool:
        return len(self.matches) > 0

    @property
    def pages_with_matches(self) -> List[int]:
        return sorted(set(m.page_number for m in self.matches))

    def matches_on_page(self, page_number: int) -> List[RegexMatch]:
        return [m for m in self.matches if m.page_number == page_number]

    def matches_with_group(self, group_name: str) -> List[RegexMatch]:
        return [m for m in self.matches if group_name in m.named_groups]


class RegexSearchEngine:
    """Advanced regex search engine for PDF documents.

    Supports full Python regex syntax including named groups, multi-line
    matching, context extraction, and detailed match statistics.
    """

    def __init__(self):
        self._index_builder = SearchIndexBuilder()
        self._compiled_cache: Dict[str, re.Pattern] = {}
        self._cache_lock = __import__("threading").Lock()

    def search(
        self,
        doc: fitz.Document,
        pattern: str,
        case_sensitive: bool = False,
        multiline: bool = True,
        dot_all: bool = False,
        max_results: int = 0,
        page_numbers: Optional[List[int]] = None,
        context_lines: int = 0,
    ) -> RegexSearchResult:
        start_time = time.time()
        compiled, compile_time = self._compile_pattern(
            pattern, case_sensitive, multiline, dot_all
        )

        if compiled is None:
            stats = MatchStatistics(
                pattern=pattern,
                is_valid=False,
                error_message="Failed to compile regex pattern",
                compile_time_ms=compile_time,
            )
            return RegexSearchResult(matches=[], statistics=stats)

        index = self._index_builder.build_index(doc)
        matches: List[RegexMatch] = []

        for page_entry in index.page_data:
            page_num = page_entry["page_number"]
            if page_numbers and page_num not in page_numbers:
                continue

            page_text = page_entry["text"]
            page_matches = self._search_page(
                page_text, compiled, page_num, page_entry
            )
            matches.extend(page_matches)

            if max_results > 0 and len(matches) >= max_results:
                matches = matches[:max_results]
                break

        search_time = (time.time() - start_time) * 1000

        ctx_lines: List[ContextLine] = []
        if context_lines > 0:
            ctx_lines = self._extract_context_lines(
                index, matches, context_lines
            )

        stats = self._compute_statistics(
            matches, pattern, compiled.flags, compile_time, search_time
        )

        return RegexSearchResult(
            matches=matches,
            statistics=stats,
            context_lines=ctx_lines,
        )

    def search_with_named_groups(
        self,
        doc: fitz.Document,
        pattern: str,
        group_names: Optional[List[str]] = None,
        case_sensitive: bool = False,
        multiline: bool = True,
    ) -> Dict[str, List[RegexMatch]]:
        compiled, _ = self._compile_pattern(pattern, case_sensitive, multiline, False)
        if compiled is None:
            return {}

        index = self._index_builder.build_index(doc)
        all_matches = self._search_index(index, compiled, None)

        result: Dict[str, List[RegexMatch]] = {}
        for match in all_matches:
            if group_names:
                for gname in group_names:
                    if gname in match.named_groups:
                        if gname not in result:
                            result[gname] = []
                        result[gname].append(match)
            else:
                for gname in match.named_groups:
                    if gname not in result:
                        result[gname] = []
                    result[gname].append(match)

        return result

    def find_all_patterns(
        self,
        doc: fitz.Document,
        patterns: List[str],
        case_sensitive: bool = False,
    ) -> Dict[str, RegexSearchResult]:
        results: Dict[str, RegexSearchResult] = {}
        for pattern in patterns:
            results[pattern] = self.search(
                doc, pattern, case_sensitive=case_sensitive
            )
        return results

    def get_match_statistics(
        self, doc: fitz.Document, pattern: str, case_sensitive: bool = False
    ) -> MatchStatistics:
        result = self.search(doc, pattern, case_sensitive=case_sensitive)
        return result.statistics

    def validate_pattern(self, pattern: str) -> Tuple[bool, str]:
        try:
            compiled = re.compile(pattern)
            return True, ""
        except re.error as e:
            return False, str(e)

    def _compile_pattern(
        self,
        pattern: str,
        case_sensitive: bool,
        multiline: bool,
        dot_all: bool,
    ) -> Tuple[Optional[re.Pattern], float]:
        cache_key = f"{pattern}:{case_sensitive}:{multiline}:{dot_all}"

        with self._cache_lock:
            if cache_key in self._compiled_cache:
                return self._compiled_cache[cache_key], 0.0

        start = time.time()
        flags = 0
        if not case_sensitive:
            flags |= re.IGNORECASE
        if multiline:
            flags |= re.MULTILINE
        if dot_all:
            flags |= re.DOTALL

        try:
            compiled = re.compile(pattern, flags)
            compile_time = (time.time() - start) * 1000
            with self._cache_lock:
                self._compiled_cache[cache_key] = compiled
            return compiled, compile_time
        except re.error as e:
            logger.warning("Regex compile error: %s", e)
            return None, (time.time() - start) * 1000

    def _search_page(
        self,
        page_text: str,
        compiled: re.Pattern,
        page_num: int,
        page_entry: Dict[str, Any],
    ) -> List[RegexMatch]:
        matches: List[RegexMatch] = []
        char_positions = page_entry.get("char_positions", [])

        for match in compiled.finditer(page_text):
            start = match.start()
            end = match.end()
            match_text = match.group()

            bbox = self._bbox_for_match(
                char_positions, start, end, page_text
            )

            groups: Dict[str, str] = {}
            named: Dict[str, Tuple[str, int, int]] = {}
            for i, g in enumerate(match.groups()):
                if g is not None:
                    groups[str(i + 1)] = g

            for name, span in match.groupdict().items():
                if span is not None:
                    group_start = match.start(name)
                    group_end = match.end(name)
                    named[name] = (span, group_start, group_end)
                    groups[name] = span

            regex_match = RegexMatch(
                text=match_text,
                page_number=page_num,
                bbox=bbox or (0.0, 0.0, 0.0, 0.0),
                start=start,
                end=end,
                groups=groups,
                named_groups=named,
                span=(start, end),
            )
            matches.append(regex_match)

        return matches

    def _search_index(
        self,
        index: SearchIndex,
        compiled: re.Pattern,
        page_numbers: Optional[List[int]],
    ) -> List[RegexMatch]:
        all_matches: List[RegexMatch] = []
        for page_entry in index.page_data:
            page_num = page_entry["page_number"]
            if page_numbers and page_num not in page_numbers:
                continue
            page_matches = self._search_page(
                page_entry["text"], compiled, page_num, page_entry
            )
            all_matches.extend(page_matches)
        return all_matches

    def _extract_context_lines(
        self,
        index: SearchIndex,
        matches: List[RegexMatch],
        context_count: int,
    ) -> List[ContextLine]:
        context_lines: List[ContextLine] = []

        for match in matches:
            page_data = None
            for pd in index.page_data:
                if pd["page_number"] == match.page_number:
                    page_data = pd
                    break
            if page_data is None:
                continue

            text = page_data["text"]
            lines = text.split("\n")
            match_line_start = text[:match.start()].count("\n")
            match_line_end = text[:match.end()].count("\n")

            line_offset = 0
            for i, line_text in enumerate(lines):
                is_match_line = match_line_start <= i <= match_line_end
                if abs(i - match_line_start) <= context_count or abs(i - match_line_end) <= context_count or is_match_line:
                    context_lines.append(ContextLine(
                        text=line_text,
                        line_number=i,
                        char_offset=line_offset,
                        is_match=is_match_line,
                    ))
                line_offset += len(line_text) + 1

        seen = set()
        unique: List[ContextLine] = []
        for cl in context_lines:
            key = (cl.line_number, cl.text)
            if key not in seen:
                seen.add(key)
                unique.append(cl)

        return sorted(unique, key=lambda c: c.line_number)

    def _compute_statistics(
        self,
        matches: List[RegexMatch],
        pattern: str,
        flags: int,
        compile_time_ms: float,
        search_time_ms: float,
    ) -> MatchStatistics:
        matches_per_page: Dict[int, int] = {}
        for m in matches:
            matches_per_page[m.page_number] = matches_per_page.get(m.page_number, 0) + 1

        group_stats: Dict[str, int] = {}
        for m in matches:
            for gname in m.named_groups:
                group_stats[gname] = group_stats.get(gname, 0) + 1

        return MatchStatistics(
            total_matches=len(matches),
            total_pages_with_matches=len(matches_per_page),
            matches_per_page=matches_per_page,
            group_stats=group_stats,
            search_time_ms=search_time_ms,
            pattern_compile_time_ms=compile_time_ms,
            pattern=pattern,
            flags=flags,
            is_valid=True,
        )

    def _bbox_for_match(
        self,
        char_positions: List[Dict[str, Any]],
        start: int,
        end: int,
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
            if start <= idx < end:
                found = True
                bbox = cp.get("bbox", (0, 0, 0, 0))
                x_min = min(x_min, bbox[0])
                y_min = min(y_min, bbox[1])
                x_max = max(x_max, bbox[2])
                y_max = max(y_max, bbox[3])

        if found and x_min < float("inf"):
            return (x_min, y_min, x_max, y_max)

        match_len = end - start
        est_x = (start / max(len(page_text), 1)) * 600
        est_w = match_len * 8.0
        return (est_x, 0.0, est_x + est_w, 12.0)

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._compiled_cache.clear()
        self._index_builder.invalidate()

    @property
    def cache_size(self) -> int:
        with self._cache_lock:
            return len(self._compiled_cache)


class PatternLibrary:
    """Pre-built regex patterns for common PDF search tasks."""

    EMAIL = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    PHONE_US = r'(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'
    URL = r'https?://[^\s<>\"\'\)]+'
    DATE_ISO = r'\d{4}[-/]\d{1,2}[-/]\d{1,2}'
    DATE_US = r'\d{1,2}/\d{1,2}/\d{2,4}'
    CURRENCY = r'[\$€£¥]\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
    SSN = r'\d{3}-\d{2}-\d{4}'
    ZIP_CODE = r'\d{5}(?:-\d{4})?'
    IP_ADDRESS = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
    SSN_ALT = r'\d{3}[\s-]\d{2}[\s-]\d{4}'
    CREDIT_CARD = r'\b(?:\d[ -]*?){13,16}\b'

    @classmethod
    def get_all_patterns(cls) -> Dict[str, str]:
        return {
            name: getattr(cls, name)
            for name in dir(cls)
            if name.isupper() and isinstance(getattr(cls, name), str)
        }

    @classmethod
    def search_for_pii(
        cls, engine: RegexSearchEngine, doc: fitz.Document
    ) -> Dict[str, RegexSearchResult]:
        pii_patterns = {
            "emails": cls.EMAIL,
            "phone_numbers": cls.PHONE_US,
            "credit_cards": cls.CREDIT_CARD,
            "ssn": cls.SSN,
            "dates": cls.DATE_ISO,
            "urls": cls.URL,
        }
        results: Dict[str, RegexSearchResult] = {}
        for name, pattern in pii_patterns.items():
            results[name] = engine.search(doc, pattern)
        return results
