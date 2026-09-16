from __future__ import annotations

from cachetools import TTLCache
from threading import RLock
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class AppCache:
    """Small process-local TTL cache. Safe for a single portfolio instance.

    The provider boundary makes this replaceable with Redis without touching
    domain analytics code when the project needs horizontal scale.
    """

    def __init__(self, maxsize: int = 512, ttl: int = 300):
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> Any:
        with self._lock:
            self._cache[key] = value
        return value

    async def get_or_set(self, key: str, loader: Callable[[], T]) -> T:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = await loader()
        self.set(key, value)
        return value
