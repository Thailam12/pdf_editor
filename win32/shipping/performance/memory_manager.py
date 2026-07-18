"""Smart memory management: track usage, prevent leaks, and optimize resource allocation."""

import gc
import os
import sys
import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    timestamp: float = 0
    total_mb: float = 0
    heap_mb: float = 0
    external_mb: float = 0
    page_cache_mb: float = 0
    render_buffer_mb: float = 0
    doc_objects_mb: float = 0
    peak_mb: float = 0


@dataclass
class MemoryBudget:
    max_total_mb: float = 2048
    max_heap_mb: float = 1024
    max_render_buffer_mb: float = 512
    max_doc_objects_mb: float = 256
    gc_threshold_mb: float = 1500
    warning_threshold_pct: float = 80.0


class MemoryManager:
    """Smart memory management with tracking, budgeting, and automatic cleanup."""

    def __init__(self, budget: MemoryBudget = None):
        self._budget = budget or MemoryBudget()
        self._snapshots: list[MemorySnapshot] = []
        self._tracked_objects: dict[str, Any] = {}
        self._object_sizes: dict[str, int] = {}
        self._on_warning: Optional[Callable] = None
        self._on_critical: Optional[Callable] = None
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._peak_memory = 0
        self._gc_count = 0

    def get_memory_usage(self) -> MemorySnapshot:
        snapshot = MemorySnapshot(timestamp=time.time())
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem = process.memory_info()
            snapshot.total_mb = mem.rss / (1024 * 1024)
            snapshot.heap_mb = getattr(mem, 'vms', mem.rss) / (1024 * 1024)
        except ImportError:
            snapshot.total_mb = sys.getsizeof(None) / 1024
        snapshot.render_buffer_mb = sum(
            sys.getsizeof(v) for v in self._tracked_objects.values()
            if isinstance(v, (bytes, bytearray))
        ) / (1024 * 1024) if self._tracked_objects else 0
        snapshot.peak_mb = self._peak_memory
        self._peak_memory = max(self._peak_memory, snapshot.total_mb)
        self._snapshots.append(snapshot)
        if len(self._snapshots) > 1000:
            self._snapshots = self._snapshots[-500:]
        return snapshot

    def check_budget(self) -> dict:
        usage = self.get_memory_usage()
        total_pct = (usage.total_mb / self._budget.max_total_mb * 100) if self._budget.max_total_mb > 0 else 0
        status = "ok"
        if total_pct >= 95:
            status = "critical"
            if self._on_critical:
                self._on_critical(usage)
        elif total_pct >= self._budget.warning_threshold_pct:
            status = "warning"
            if self._on_warning:
                self._on_warning(usage)
        return {
            "status": status,
            "total_mb": usage.total_mb,
            "budget_mb": self._budget.max_total_mb,
            "usage_pct": round(total_pct, 1),
            "heap_mb": usage.heap_mb,
            "render_buffer_mb": usage.render_buffer_mb,
            "peak_mb": usage.peak_mb,
            "gc_count": self._gc_count,
        }

    def track_object(self, key: str, obj: Any):
        self._tracked_objects[key] = obj
        self._object_sizes[key] = sys.getsizeof(obj)

    def untrack_object(self, key: str):
        self._tracked_objects.pop(key, None)
        self._object_sizes.pop(key, None)

    def force_gc(self) -> dict:
        before = sys.getsizeof(None)
        collected = gc.collect()
        self._gc_count += 1
        after = sys.getsizeof(None)
        return {"collected": collected, "gc_count": self._gc_count}

    def auto_cleanup(self) -> dict:
        usage = self.get_memory_usage()
        cleaned = 0
        if usage.total_mb > self._budget.gc_threshold_mb:
            result = self.force_gc()
            cleaned = result.get("collected", 0)
        if usage.render_buffer_mb > self._budget.max_render_buffer_mb:
            keys_to_remove = []
            for key, obj in self._tracked_objects.items():
                if isinstance(obj, (bytes, bytearray)):
                    keys_to_remove.append(key)
            for key in keys_to_remove[:len(keys_to_remove) // 2]:
                del self._tracked_objects[key]
                self._object_sizes.pop(key, None)
                cleaned += 1
        return {"cleaned_items": cleaned, "gc_count": self._gc_count}

    def register_warning_callback(self, callback: Callable):
        self._on_warning = callback

    def register_critical_callback(self, callback: Callable):
        self._on_critical = callback

    def start_monitoring(self, interval_sec: float = 5.0):
        self._monitoring = True
        def _monitor_loop():
            while self._monitoring:
                self.auto_cleanup()
                time.sleep(interval_sec)
        self._monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        self._monitoring = False

    def get_tracked_objects(self) -> dict:
        return {k: {"size_bytes": self._object_sizes.get(k, 0),
                     "type": type(v).__name__}
                for k, v in self._tracked_objects.items()}

    def get_memory_history(self, limit: int = 100) -> list[dict]:
        return [
            {"timestamp": s.timestamp, "total_mb": s.total_mb, "heap_mb": s.heap_mb,
             "render_buffer_mb": s.render_buffer_mb, "peak_mb": s.peak_mb}
            for s in self._snapshots[-limit:]
        ]

    def get_report(self) -> dict:
        usage = self.get_memory_usage()
        budget = self.check_budget()
        return {
            "current": budget,
            "tracked_objects": len(self._tracked_objects),
            "tracked_size_mb": sum(self._object_sizes.values()) / (1024 * 1024),
            "snapshots_count": len(self._snapshots),
            "gc_count": self._gc_count,
            "monitoring": self._monitoring,
        }
