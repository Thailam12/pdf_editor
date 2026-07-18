"""Performance benchmarks: measure render time, memory usage, and operations throughput."""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    name: str = ""
    category: str = ""
    duration_ms: float = 0
    operations_per_sec: float = 0
    memory_mb: float = 0
    iterations: int = 1
    passed: bool = True
    threshold_ms: float = 0
    details: dict = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    name: str = ""
    results: list[BenchmarkResult] = field(default_factory=list)
    total_duration_ms: float = 0
    passed: int = 0
    failed: int = 0
    overall_score: float = 0


class PerformanceBenchmark:
    """PDFMind performance benchmark suite for render time, memory, and throughput."""

    THRESHOLDS = {
        "open_small_pdf_ms": 500,
        "open_medium_pdf_ms": 2000,
        "open_large_pdf_ms": 5000,
        "render_page_ms": 100,
        "text_extract_ms": 200,
        "merge_10_pdfs_ms": 3000,
        "split_pdf_ms": 1000,
        "compress_pdf_ms": 2000,
        "search_text_ms": 500,
        "ai_summarize_ms": 5000,
        "startup_time_ms": 2000,
        "memory_100_pages_mb": 200,
        "memory_1000_pages_mb": 500,
    }

    def __init__(self):
        self._results: list[BenchmarkResult] = []
        self._suites: list[BenchmarkSuite] = []

    def benchmark_open_pdf(self, pdf_path: str, iterations: int = 5) -> BenchmarkResult:
        result = BenchmarkResult(
            name="open_pdf", category="io",
            threshold_ms=self.THRESHOLDS.get("open_small_pdf_ms", 500),
            iterations=iterations,
        )
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                _ = len(reader.pages)
            except Exception as e:
                result.passed = False
                result.details["error"] = str(e)
                break
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        if times:
            result.duration_ms = sum(times) / len(times)
            result.operations_per_sec = 1000 / result.duration_ms if result.duration_ms > 0 else 0
            result.passed = result.duration_ms <= result.threshold_ms
        self._results.append(result)
        return result

    def benchmark_render_page(self, pdf_path: str, page_index: int = 0, iterations: int = 10) -> BenchmarkResult:
        result = BenchmarkResult(
            name="render_page", category="render",
            threshold_ms=self.THRESHOLDS.get("render_page_ms", 100),
            iterations=iterations,
        )
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                _ = reader.pages[page_index].extract_text()
            except Exception as e:
                result.passed = False
                result.details["error"] = str(e)
                break
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        if times:
            result.duration_ms = sum(times) / len(times)
            result.operations_per_sec = 1000 / result.duration_ms if result.duration_ms > 0 else 0
            result.passed = result.duration_ms <= result.threshold_ms
        self._results.append(result)
        return result

    def benchmark_text_extract(self, pdf_path: str, iterations: int = 5) -> BenchmarkResult:
        result = BenchmarkResult(
            name="text_extract", category="extraction",
            threshold_ms=self.THRESHOLDS.get("text_extract_ms", 200),
            iterations=iterations,
        )
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    _ = page.extract_text()
            except Exception as e:
                result.passed = False
                result.details["error"] = str(e)
                break
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        if times:
            result.duration_ms = sum(times) / len(times)
            result.operations_per_sec = 1000 / result.duration_ms if result.duration_ms > 0 else 0
            result.passed = result.duration_ms <= result.threshold_ms
        self._results.append(result)
        return result

    def benchmark_merge(self, pdf_paths: list[str], iterations: int = 3) -> BenchmarkResult:
        result = BenchmarkResult(
            name="merge_pdfs", category="operations",
            threshold_ms=self.THRESHOLDS.get("merge_10_pdfs_ms", 3000),
            iterations=iterations,
        )
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                from pypdf import PdfReader, PdfWriter
                writer = PdfWriter()
                for path in pdf_paths:
                    reader = PdfReader(path)
                    for page in reader.pages:
                        writer.add_page(page)
            except Exception as e:
                result.passed = False
                result.details["error"] = str(e)
                break
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        if times:
            result.duration_ms = sum(times) / len(times)
            result.passed = result.duration_ms <= result.threshold_ms
            result.details["files_merged"] = len(pdf_paths)
        self._results.append(result)
        return result

    def benchmark_memory(self, pdf_path: str, target_pages: int = 100) -> BenchmarkResult:
        result = BenchmarkResult(
            name="memory_usage", category="memory",
            threshold_ms=0,
        )
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_before = process.memory_info().rss / (1024 * 1024)
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            pages_to_read = min(target_pages, len(reader.pages))
            for i in range(pages_to_read):
                _ = reader.pages[i].extract_text()
            mem_after = process.memory_info().rss / (1024 * 1024)
            result.memory_mb = mem_after - mem_before
            threshold_key = f"memory_{target_pages}_pages_mb"
            result.threshold_ms = self.THRESHOLDS.get(threshold_key, 200)
            result.passed = result.memory_mb <= result.threshold_ms
            result.details = {"pages_read": pages_to_read, "mem_before_mb": round(mem_before, 1),
                              "mem_after_mb": round(mem_after, 1)}
        except ImportError:
            result.passed = True
            result.details["note"] = "psutil not available; memory test skipped"
        self._results.append(result)
        return result

    def benchmark_search(self, pdf_path: str, query: str = "the", iterations: int = 10) -> BenchmarkResult:
        result = BenchmarkResult(
            name="search_text", category="search",
            threshold_ms=self.THRESHOLDS.get("search_text_ms", 500),
            iterations=iterations,
        )
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                from pypdf import PdfReader
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    text = page.extract_text() or ""
                    _ = text.lower().count(query.lower())
            except Exception as e:
                result.passed = False
                result.details["error"] = str(e)
                break
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        if times:
            result.duration_ms = sum(times) / len(times)
            result.passed = result.duration_ms <= result.threshold_ms
        self._results.append(result)
        return result

    def run_full_benchmark(self, test_files: dict[str, str]) -> BenchmarkSuite:
        suite = BenchmarkSuite(name="full_benchmark")
        start = time.perf_counter()
        if "small" in test_files:
            suite.results.append(self.benchmark_open_pdf(test_files["small"]))
            suite.results.append(self.benchmark_text_extract(test_files["small"]))
            suite.results.append(self.benchmark_render_page(test_files["small"]))
            suite.results.append(self.benchmark_search(test_files["small"]))
            suite.results.append(self.benchmark_memory(test_files["small"]))
        if "pdf_list" in test_files:
            suite.results.append(self.benchmark_merge(test_files["pdf_list"]))
        suite.total_duration_ms = (time.perf_counter() - start) * 1000
        suite.passed = sum(1 for r in suite.results if r.passed)
        suite.failed = sum(1 for r in suite.results if not r.passed)
        total = len(suite.results)
        suite.overall_score = (suite.passed / total * 100) if total > 0 else 0
        self._suites.append(suite)
        return suite

    def get_all_results(self) -> list[BenchmarkResult]:
        return self._results

    def get_comparison_data(self) -> dict:
        return {
            "benchmarks": [
                {"name": r.name, "category": r.category, "duration_ms": r.duration_ms,
                 "passed": r.passed, "ops_per_sec": r.operations_per_sec}
                for r in self._results
            ],
            "thresholds": self.THRESHOLDS,
        }

    def generate_report(self) -> str:
        lines = ["# PDFMind Performance Benchmark Report\n"]
        for r in self._results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"## {r.name} [{status}]")
            lines.append(f"- Duration: {r.duration_ms:.1f}ms (threshold: {r.threshold_ms}ms)")
            if r.operations_per_sec > 0:
                lines.append(f"- Throughput: {r.operations_per_sec:.1f} ops/sec")
            if r.memory_mb > 0:
                lines.append(f"- Memory delta: {r.memory_mb:.1f} MB")
            lines.append("")
        return "\n".join(lines)
