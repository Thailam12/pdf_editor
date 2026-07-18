"""Multi-level caching: LRU page cache, render cache, and disk cache for fast document access."""

import os
import time
import json
import hashlib
import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    key: str = ""
    value: Any = None
    size_bytes: int = 0
    created_at: float = 0
    last_accessed: float = 0
    access_count: int = 0
    ttl_seconds: float = 0
    is_pinned: bool = False


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0


class LRUCache:
    """Thread-safe LRU cache with TTL support and size limits."""

    def __init__(self, max_size: int = 100, max_bytes: int = 100 * 1024 * 1024):
        self._max_size = max_size
        self._max_bytes = max_bytes
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats.misses += 1
                self._update_hit_rate()
                return None
            if entry.ttl_seconds > 0 and time.time() - entry.created_at > entry.ttl_seconds:
                del self._cache[key]
                self._stats.misses += 1
                self._update_hit_rate()
                return None
            self._cache.move_to_end(key)
            entry.last_accessed = time.time()
            entry.access_count += 1
            self._stats.hits += 1
            self._update_hit_rate()
            return entry.value

    def put(self, key: str, value: Any, ttl_seconds: float = 0, size_bytes: int = 0) -> bool:
        with self._lock:
            if size_bytes == 0:
                try:
                    import sys
                    size_bytes = sys.getsizeof(value)
                except Exception:
                    size_bytes = 1024
            if key in self._cache:
                self._cache.move_to_end(key)
                entry = self._cache[key]
                entry.value = value
                entry.size_bytes = size_bytes
                entry.last_accessed = time.time()
                return True
            self._evict_until_fit(size_bytes)
            entry = CacheEntry(
                key=key, value=value, size_bytes=size_bytes,
                created_at=time.time(), last_accessed=time.time(),
                ttl_seconds=ttl_seconds,
            )
            self._cache[key] = entry
            self._stats.entry_count = len(self._cache)
            self._stats.size_bytes += size_bytes
            return True

    def remove(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._stats.size_bytes -= entry.size_bytes
                self._stats.entry_count = len(self._cache)
                return True
            return False

    def contains(self, key: str) -> bool:
        with self._lock:
            if key not in self._cache:
                return False
            entry = self._cache[key]
            if entry.ttl_seconds > 0 and time.time() - entry.created_at > entry.ttl_seconds:
                del self._cache[key]
                return False
            return True

    def _evict_until_fit(self, needed_bytes: int):
        while (len(self._cache) >= self._max_size or
               self._stats.size_bytes + needed_bytes > self._max_bytes):
            if not self._cache:
                break
            key, entry = next(iter(self._cache.items()))
            if entry.is_pinned:
                self._cache.move_to_end(key)
                if len(self._cache) <= 1:
                    break
                continue
            self._stats.size_bytes -= entry.size_bytes
            del self._cache[key]
            self._stats.evictions += 1
        self._stats.entry_count = len(self._cache)

    def _update_hit_rate(self):
        total = self._stats.hits + self._stats.misses
        self._stats.hit_rate = (self._stats.hits / total * 100) if total > 0 else 0

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._stats = CacheStats()

    def get_stats(self) -> CacheStats:
        return CacheStats(
            hits=self._stats.hits, misses=self._stats.misses,
            evictions=self._stats.evictions, size_bytes=self._stats.size_bytes,
            entry_count=self._stats.entry_count, hit_rate=self._stats.hit_rate,
        )

    def get_keys(self) -> list[str]:
        with self._lock:
            return list(self._cache.keys())


class DiskCache:
    """Persistent disk cache for rendered pages and metadata."""

    def __init__(self, cache_dir: str = None, max_size_mb: int = 500):
        import tempfile
        self._cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "pdfmind_cache")
        self._max_size_mb = max_size_mb
        os.makedirs(self._cache_dir, exist_ok=True)

    def _key_path(self, key: str) -> str:
        safe = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self._cache_dir, f"{safe}.cache")

    def get(self, key: str) -> Optional[bytes]:
        path = self._key_path(key)
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    data = f.read()
                os.utime(path, None)
                return data
            except Exception:
                pass
        return None

    def put(self, key: str, data: bytes):
        try:
            path = self._key_path(key)
            with open(path, "wb") as f:
                f.write(data)
            self._cleanup_if_needed()
        except Exception as e:
            logger.error(f"Disk cache write failed: {e}")

    def remove(self, key: str):
        try:
            path = self._key_path(key)
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    def _cleanup_if_needed(self):
        total = sum(
            os.path.getsize(os.path.join(self._cache_dir, f))
            for f in os.listdir(self._cache_dir)
            if f.endswith(".cache")
        )
        target = self._max_size_mb * 1024 * 1024
        if total <= target:
            return
        files = sorted(
            [os.path.join(self._cache_dir, f) for f in os.listdir(self._cache_dir)
             if f.endswith(".cache")],
            key=os.path.getatime,
        )
        for fp in files:
            if total <= target * 0.8:
                break
            size = os.path.getsize(fp)
            try:
                os.remove(fp)
                total -= size
            except Exception:
                pass

    def clear(self):
        for f in os.listdir(self._cache_dir):
            if f.endswith(".cache"):
                try:
                    os.remove(os.path.join(self._cache_dir, f))
                except Exception:
                    pass

    def get_size_mb(self) -> float:
        total = sum(
            os.path.getsize(os.path.join(self._cache_dir, f))
            for f in os.listdir(self._cache_dir)
            if f.endswith(".cache")
        )
        return total / (1024 * 1024)


class CacheSystem:
    """Multi-level cache system: L1 (memory LRU) + L2 (disk persistent)."""

    def __init__(self, l1_max_size: int = 100, l1_max_bytes: int = 256 * 1024 * 1024,
                 l2_max_mb: int = 500, disk_cache_dir: str = None):
        self._l1 = LRUCache(max_size=l1_max_size, max_bytes=l1_max_bytes)
        self._l2 = DiskCache(cache_dir=disk_cache_dir, max_size_mb=l2_max_mb)

    def get(self, key: str) -> Optional[Any]:
        value = self._l1.get(key)
        if value is not None:
            return value
        data = self._l2.get(key)
        if data is not None:
            self._l1.put(key, data)
            return data
        return None

    def put(self, key: str, value: Any, persist: bool = True):
        self._l1.put(key, value)
        if persist and isinstance(value, (bytes, bytearray)):
            self._l2.put(key, value)

    def remove(self, key: str):
        self._l1.remove(key)
        self._l2.remove(key)

    def contains(self, key: str) -> bool:
        return self._l1.contains(key) or self._l2.get(key) is not None

    def clear(self):
        self._l1.clear()
        self._l2.clear()

    def get_stats(self) -> dict:
        l1_stats = self._l1.get_stats()
        return {
            "l1": {
                "hits": l1_stats.hits, "misses": l1_stats.misses,
                "evictions": l1_stats.evictions, "entries": l1_stats.entry_count,
                "size_mb": round(l1_stats.size_bytes / (1024 * 1024), 2),
                "hit_rate": round(l1_stats.hit_rate, 1),
            },
            "l2": {"size_mb": round(self._l2.get_size_mb(), 2)},
        }
