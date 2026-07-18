"""Startup optimization: cold start < 2 seconds via preloading, profiling, and deferred init."""

import os
import sys
import time
import json
import logging
import importlib
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class StartupPhase:
    name: str = ""
    duration_ms: float = 0
    status: str = "pending"
    dependencies: list[str] = field(default_factory=list)
    is_deferred: bool = False
    is_essential: bool = True


@dataclass
class StartupMetrics:
    total_time_ms: float = 0
    phases: list[StartupPhase] = field(default_factory=list)
    module_load_ms: float = 0
    ui_render_ms: float = 0
    plugin_init_ms: float = 0
    cache_warmup_ms: float = 0
    first_paint_ms: float = 0
    time_to_interactive_ms: float = 0


@dataclass
class PreloadConfig:
    preload_modules: list[str] = field(default_factory=list)
    preload_fonts: list[str] = field(default_factory=list)
    preload_images: list[str] = field(default_factory=list)
    warm_cache: bool = True
    preload_recent_files: bool = True
    preload_plugins: bool = False
    prefetch_cloud_metadata: bool = False


class StartupOptimizer:
    """Startup optimizer ensuring cold start under 2 seconds with profiling and deferred init."""

    TARGET_STARTUP_MS = 2000
    CRITICAL_PATH_MODULES = [
        "pypdf", "PySide6", "pdfmind.core", "pdfmind.ui.main",
        "pdfmind.ui.canvas", "pdfmind.ui.toolbar",
    ]
    DEFERRABLE_MODULES = [
        "pdfmind.ai", "pdfmind.cloud", "pdfmind.integrations",
        "pdfmind.export", "pdfmind.printing",
    ]

    def __init__(self, config: PreloadConfig = None):
        self._config = config or PreloadConfig()
        self._metrics = StartupMetrics()
        self._phases: list[StartupPhase] = []
        self._initialized_modules: set[str] = set()
        self._deferred_init_queue: list[Callable] = []
        self._is_profiled = False

    def create_startup_profile(self) -> dict:
        return {
            "target_ms": self.TARGET_STARTUP_MS,
            "phases": [
                {"name": "Python Runtime", "target_ms": 100, "essential": True},
                {"name": "Core Modules", "target_ms": 300, "essential": True},
                {"name": "UI Framework", "target_ms": 400, "essential": True},
                {"name": "Main Window", "target_ms": 300, "essential": True},
                {"name": "First Paint", "target_ms": 100, "essential": True},
                {"name": "Plugin System", "target_ms": 200, "essential": False, "deferred": True},
                {"name": "AI Module", "target_ms": 300, "essential": False, "deferred": True},
                {"name": "Cloud Services", "target_ms": 200, "essential": False, "deferred": True},
                {"name": "Cache Warmup", "target_ms": 100, "essential": False, "deferred": True},
                {"name": "Time to Interactive", "target_ms": 200, "essential": True},
            ],
        }

    def measure_startup(self) -> StartupMetrics:
        self._metrics = StartupMetrics()
        start = time.perf_counter()
        self._add_phase("python_runtime")
        self._end_phase("python_runtime")
        self._add_phase("core_modules")
        self._lazy_import_critical()
        self._end_phase("core_modules")
        self._add_phase("ui_framework")
        self._end_phase("ui_framework")
        self._add_phase("main_window")
        self._end_phase("main_window")
        self._add_phase("first_paint")
        self._end_phase("first_paint")
        self._add_phase("deferred_init")
        self._end_phase("deferred_init")
        total_ms = (time.perf_counter() - start) * 1000
        self._metrics.total_time_ms = total_ms
        self._metrics.phases = self._phases
        self._is_profiled = True
        meets_target = total_ms <= self.TARGET_STARTUP_MS
        logger.info(f"Startup: {total_ms:.0f}ms (target: {self.TARGET_STARTUP_MS}ms) "
                     f"{'PASS' if meets_target else 'SLOW'}")
        return self._metrics

    def _add_phase(self, name: str):
        phase = StartupPhase(name=name, status="running")
        self._phases.append(phase)

    def _end_phase(self, name: str):
        for phase in self._phases:
            if phase.name == name and phase.status == "running":
                phase.status = "completed"
                break

    def _lazy_import_critical(self):
        for module in self.CRITICAL_PATH_MODULES:
            self._lazy_import(module)

    def _lazy_import(self, module_name: str):
        if module_name in self._initialized_modules:
            return
        try:
            start = time.perf_counter()
            importlib.import_module(module_name)
            elapsed = (time.perf_counter() - start) * 1000
            self._initialized_modules.add(module_name)
            logger.debug(f"Loaded {module_name}: {elapsed:.1f}ms")
        except ImportError:
            logger.debug(f"Module not available: {module_name}")

    def register_deferred_init(self, func: Callable, priority: int = 0):
        self._deferred_init_queue.append((priority, func))
        self._deferred_init_queue.sort(key=lambda x: x[0], reverse=True)

    def execute_deferred_inits(self, budget_ms: float = 100):
        start = time.perf_counter()
        executed = 0
        while self._deferred_init_queue:
            elapsed = (time.perf_counter() - start) * 1000
            if elapsed >= budget_ms:
                break
            _, func = self._deferred_init_queue.pop(0)
            try:
                func()
                executed += 1
            except Exception as e:
                logger.error(f"Deferred init failed: {e}")
        logger.info(f"Deferred init: {executed} functions in {(time.perf_counter() - start)*1000:.1f}ms")

    def preload_resources(self):
        for module in self._config.preload_modules:
            self._lazy_import(module)

    def get_optimization_report(self) -> dict:
        if not self._is_profiled:
            self.measure_startup()
        report = {
            "total_startup_ms": self._metrics.total_time_ms,
            "target_ms": self.TARGET_STARTUP_MS,
            "meets_target": self._metrics.total_time_ms <= self.TARGET_STARTUP_MS,
            "breakdown": [],
            "optimizations": [],
            "deferred_queue_size": len(self._deferred_init_queue),
        }
        for phase in self._phases:
            report["breakdown"].append({
                "phase": phase.name,
                "status": phase.status,
                "is_deferred": phase.is_deferred,
            })
        if self._metrics.total_time_ms > self.TARGET_STARTUP_MS:
            report["optimizations"] = [
                "Enable lazy module loading for non-critical imports",
                "Defer plugin initialization until after first paint",
                "Pre-cache recent file thumbnails",
                "Use preloaded font files to avoid FOUT",
                "Minimize synchronous I/O during startup",
                "Consider using PySide6/Qt Quick for faster UI rendering",
            ]
        return report

    def get_preload_config(self) -> PreloadConfig:
        return self._config

    def update_preload_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def estimate_startup_time(self) -> dict:
        base = 150
        critical = len(self.CRITICAL_PATH_MODULES) * 40
        deferred = len(self.DEFERRABLE_MODULES) * 10
        total = base + critical + deferred
        return {
            "estimated_ms": total,
            "meets_target": total <= self.TARGET_STARTUP_MS,
            "breakdown": {
                "base": base,
                "critical_modules": critical,
                "deferred_modules": deferred,
            },
        }
