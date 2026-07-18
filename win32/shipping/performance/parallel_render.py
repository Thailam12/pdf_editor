"""Multi-threaded parallel rendering for fast document processing and page rendering."""

import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class RenderTask:
    task_id: int = 0
    page_index: int = 0
    priority: int = 0
    render_func: Optional[Callable] = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    status: str = "pending"
    result: Any = None
    error: str = ""
    start_time: float = 0
    end_time: float = 0


@dataclass
class RenderStats:
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    in_progress: int = 0
    total_time_ms: float = 0
    avg_time_per_page_ms: float = 0
    pages_per_second: float = 0
    worker_count: int = 0
    queue_size: int = 0


class ParallelRenderer:
    """Multi-threaded page renderer for concurrent PDF page processing."""

    def __init__(self, max_workers: int = None):
        import os
        self._max_workers = max_workers or min(os.cpu_count() or 4, 8)
        self._executor: Optional[ThreadPoolExecutor] = None
        self._tasks: dict[int, RenderTask] = {}
        self._task_counter = 0
        self._lock = threading.Lock()
        self._stats = RenderStats(worker_count=self._max_workers)
        self._results: dict[int, Any] = {}
        self._completed_callbacks: list[Callable] = []
        self._batch_callbacks: dict[int, Callable] = {}

    def start(self):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
            logger.info(f"Parallel renderer started with {self._max_workers} workers")

    def stop(self):
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    def render_page(self, page_index: int, render_func: Callable,
                    args: tuple = (), kwargs: dict = None, priority: int = 0) -> int:
        self.start()
        with self._lock:
            self._task_counter += 1
            task_id = self._task_counter
            task = RenderTask(
                task_id=task_id, page_index=page_index, priority=priority,
                render_func=render_func, args=args, kwargs=kwargs or {},
                status="queued",
            )
            self._tasks[task_id] = task
        future = self._executor.submit(self._execute_task, task)
        future.add_done_callback(lambda f: self._on_task_done(task_id, f))
        return task_id

    def render_pages_batch(self, page_indices: list[int], render_func: Callable,
                           progress_callback: Callable = None) -> dict[int, Any]:
        self.start()
        futures = {}
        for idx in page_indices:
            with self._lock:
                self._task_counter += 1
                task_id = self._task_counter
                task = RenderTask(
                    task_id=task_id, page_index=idx,
                    render_func=render_func, args=(idx,),
                    status="queued",
                )
                self._tasks[task_id] = task
            future = self._executor.submit(self._execute_task, task)
            futures[future] = idx
        results = {}
        completed = 0
        total = len(page_indices)
        for future in as_completed(futures):
            page_idx = futures[future]
            try:
                result = future.result(timeout=30)
                results[page_idx] = result
            except Exception as e:
                logger.error(f"Render failed for page {page_idx}: {e}")
                results[page_idx] = None
            completed += 1
            if progress_callback:
                progress_callback(completed, total, page_idx)
        return results

    def render_all_pages(self, total_pages: int, render_func: Callable,
                         progress_callback: Callable = None) -> dict[int, Any]:
        indices = list(range(total_pages))
        return self.render_pages_batch(indices, render_func, progress_callback)

    def render_with_priority(self, tasks: list[tuple[int, Callable, int]]) -> dict[int, Any]:
        self.start()
        futures = {}
        for page_idx, func, priority in tasks:
            with self._lock:
                self._task_counter += 1
                task_id = self._task_counter
                task = RenderTask(
                    task_id=task_id, page_index=page_idx, priority=priority,
                    render_func=func, args=(page_idx,), status="queued",
                )
                self._tasks[task_id] = task
            future = self._executor.submit(self._execute_task, task)
            futures[future] = page_idx
        results = {}
        for future in as_completed(futures):
            page_idx = futures[future]
            try:
                results[page_idx] = future.result(timeout=30)
            except Exception:
                results[page_idx] = None
        return results

    def _execute_task(self, task: RenderTask) -> Any:
        task.status = "running"
        task.start_time = time.time()
        try:
            result = task.render_func(*task.args, **task.kwargs)
            task.result = result
            task.status = "completed"
            return result
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            raise
        finally:
            task.end_time = time.time()
            with self._lock:
                self._stats.completed += 1 if task.status == "completed" else 0
                self._stats.failed += 1 if task.status == "failed" else 0

    def _on_task_done(self, task_id: int, future):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                if task.status == "completed":
                    self._results[task.page_index] = task.result
                self._stats.total_time_ms = (task.end_time - task.start_time) * 1000
                if self._stats.completed > 0:
                    self._stats.avg_time_per_page_ms = (
                        self._stats.total_time_ms / self._stats.completed
                    )
                    self._stats.pages_per_second = (
                        1000 / self._stats.avg_time_per_page_ms
                        if self._stats.avg_time_per_page_ms > 0 else 0
                    )
        for cb in self._completed_callbacks:
            try:
                cb(task_id, future)
            except Exception:
                pass

    def cancel_all(self):
        with self._lock:
            for task in self._tasks.values():
                if task.status in ("pending", "queued"):
                    task.status = "cancelled"

    def get_task_status(self, task_id: int) -> Optional[RenderTask]:
        return self._tasks.get(task_id)

    def get_stats(self) -> RenderStats:
        with self._lock:
            self._stats.in_progress = sum(
                1 for t in self._tasks.values() if t.status in ("queued", "running")
            )
            self._stats.total_tasks = len(self._tasks)
            self._stats.queue_size = sum(1 for t in self._tasks.values() if t.status == "queued")
        return self._stats

    def on_page_completed(self, callback: Callable):
        self._completed_callbacks.append(callback)

    def get_result(self, page_index: int) -> Optional[Any]:
        return self._results.get(page_index)
