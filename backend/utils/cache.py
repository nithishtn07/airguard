import time
from typing import Any, Optional, Dict, Tuple
from config.settings import settings
from backend.utils.logger import logger


class SimpleTTLCache:
    """
    Lightweight, thread-safe in-memory TTL cache to prevent API flooding and rate limits.
    """
    def __init__(self, default_ttl: int = 60):
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        expires_at, value = self._cache[key]
        if time.time() > expires_at:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        duration = ttl if ttl is not None else self.default_ttl
        self._cache[key] = (time.time() + duration, value)

    def clear(self) -> None:
        self._cache.clear()


# Shared instances for live air quality and weather caching
cache = SimpleTTLCache(default_ttl=settings.CACHE_TTL_SECONDS)
