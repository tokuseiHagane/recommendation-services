"""
UpdateCacheTask: Обновление PostObjectsCache.

Porto Architecture Task:
- Атомарная операция обновления кэша
- Делегирует к PostObjectsCache.put_channels()
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


async def update_cache_task(
    cache: Any,  # PostObjectsCache
    channels: List[Dict[str, Any]]
) -> int:
    """
    Task: Обновить кэш каналов.
    
    Atomic operation для добавления каналов в PostObjectsCache.
    
    Args:
        cache: PostObjectsCache instance (DI)
        channels: Список каналов для добавления в кэш
            Expected keys: id, name, type
    
    Returns:
        Количество добавленных каналов
        
    Example:
        >>> cache = PostObjectsCache()
        >>> channels = [{"id": 123, "name": "Tech", "type": "public"}]
        >>> count = await update_cache_task(cache, channels)
        >>> count
        1
    """
    
    count = await cache.put_channels(channels)
    logger.debug(f"Updated cache with {count} channels")
    return count

