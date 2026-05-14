"""Cache module for Redis integration."""

import json
from typing import Any

import logfire
from litestar.stores.redis import RedisStore


class Cache:
    """Cache wrapper for Redis operations."""

    def __init__(self, store: RedisStore):
        """Initialize cache with Redis store.

        Args:
            store: Litestar RedisStore instance
        """
        self._store = store

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        try:
            value = await self._store.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logfire.warning("Cache get error", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        try:
            serialized = json.dumps(value, default=str)
            await self._store.set(key, serialized, expires_in=ttl)
            return True
        except Exception as e:
            logfire.warning("Cache set error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        try:
            await self._store.delete(key)
            return True
        except Exception as e:
            logfire.warning("Cache delete error", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        try:
            return await self._store.exists(key)
        except Exception as e:
            logfire.warning("Cache exists check error", key=key, error=str(e))
            return False


def create_cache_from_store(store: RedisStore) -> Cache:
    """Create Cache instance from RedisStore.

    Args:
        store: Litestar RedisStore instance

    Returns:
        Cache instance
    """
    return Cache(store)
