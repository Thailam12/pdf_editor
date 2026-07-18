"""Lazy page loading: only render visible pages with virtual scrolling and prefetching."""

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class PageRenderTask:
    page_index: int = 0
    priority: int = 0
    callback: Optional[Callable] = None
    is_cancelled: bool = False
    is_completed: bool = False
    render_time_ms: float = 0


@dataclass
class ViewportState:
    scroll_y: float = 0
    visible_height: float = 0
    page_height: float = 842
    zoom_level: float = 1.0
    visible_pages: list[int] = field(default_factory=list)
    buffer_pages_above: int = 2
    buffer_pages_below: int = 3


class LazyPageLoader:
    """Virtual page loading that renders only visible pages with intelligent prefetching."""

    def __init__(self, total_pages: int = 0, page_height: float = 842):
        self._total_pages = total_pages
        self._page_height = page_height
        self._cache: dict[int, bytes] = {}
        self._render_tasks: dict[int, PageRenderTask] = {}
        self._viewport = ViewportState(page_height=page_height)
        self._render_queue: list[PageRenderTask] = []
        self._lock = threading.Lock()
        self._render_func: Optional[Callable] = None
        self._on_page_ready: Optional[Callable] = None
        self._max_cache_size = 50
        self._prefetch_enabled = True

    def set_total_pages(self, count: int):
        self._total_pages = count

    def set_render_function(self, func: Callable):
        self._render_func = func

    def set_page_ready_callback(self, callback: Callable):
        self._on_page_ready = callback

    def update_viewport(self, scroll_y: float, visible_height: float, zoom: float = 1.0):
        self._viewport.scroll_y = scroll_y
        self._viewport.visible_height = visible_height
        self._viewport.zoom_level = zoom
        self._recalculate_visible_pages()
        self._schedule_visible_page_renders()

    def _recalculate_visible_pages(self):
        page_h = self._page_height * self._viewport.zoom_level
        if page_h <= 0:
            return
        start = max(0, int(self._viewport.scroll_y / page_h) - self._viewport.buffer_pages_above)
        end = int((self._viewport.scroll_y + self._viewport.visible_height) / page_h) + self._viewport.buffer_pages_below
        end = min(end, self._total_pages - 1)
        self._viewport.visible_pages = list(range(start, end + 1))

    def _schedule_visible_page_renders(self):
        for page_idx in self._viewport.visible_pages:
            if page_idx in self._cache:
                continue
            if page_idx in self._render_tasks and not self._render_tasks[page_idx].is_cancelled:
                continue
            self._enqueue_render(page_idx)

    def _enqueue_render(self, page_index: int):
        distance = abs(page_index - (self._viewport.visible_pages[0] if self._viewport.visible_pages else 0))
        task = PageRenderTask(page_index=page_index, priority=100 - distance)
        with self._lock:
            self._render_tasks[page_index] = task
            self._render_queue.append(task)
            self._render_queue.sort(key=lambda t: t.priority, reverse=True)

    def get_page(self, page_index: int) -> Optional[bytes]:
        if page_index in self._cache:
            return self._cache[page_index]
        self._enqueue_render(page_index)
        return None

    def get_visible_pages(self) -> list[int]:
        return list(self._viewport.visible_pages)

    def is_page_cached(self, page_index: int) -> bool:
        return page_index in self._cache

    def cache_page(self, page_index: int, data: bytes):
        with self._lock:
            self._cache[page_index] = data
            if page_index in self._render_tasks:
                self._render_tasks[page_index].is_completed = True
            self._evict_if_needed()
        if self._on_page_ready:
            self._on_page_ready(page_index, data)

    def cancel_render(self, page_index: int):
        with self._lock:
            if page_index in self._render_tasks:
                self._render_tasks[page_index].is_cancelled = True

    def _evict_if_needed(self):
        while len(self._cache) > self._max_cache_size:
            furthest = max(self._cache.keys(),
                           key=lambda p: min(abs(p - v) for v in self._viewport.visible_pages)
                           if self._viewport.visible_pages else p)
            del self._cache[furthest]

    def clear_cache(self):
        with self._lock:
            self._cache.clear()
            self._render_tasks.clear()
            self._render_queue.clear()

    def get_next_task(self) -> Optional[PageRenderTask]:
        with self._lock:
            while self._render_queue:
                task = self._render_queue.pop(0)
                if not task.is_cancelled and not task.is_completed and task.page_index not in self._cache:
                    return task
        return None

    def get_stats(self) -> dict:
        return {
            "total_pages": self._total_pages,
            "cached_pages": len(self._cache),
            "pending_renders": len([t for t in self._render_tasks.values()
                                    if not t.is_completed and not t.is_cancelled]),
            "visible_pages": self._viewport.visible_pages,
            "cache_hit_rate": 0.0,
            "max_cache_size": self._max_cache_size,
        }
