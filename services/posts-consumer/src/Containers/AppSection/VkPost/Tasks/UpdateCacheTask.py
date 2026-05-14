"""
UpdateCacheTask: Обновление кэша VK групп.

Porto Architecture Task:
- Атомарная операция обновления кэша
- Делегирует к VkGroupsCache.put_groups()
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


async def update_cache_task(
    cache: Any,  # VkGroupsCache
    groups: List[Dict[str, Any]]
) -> int:
    """
    Task: Обновить кэш VK групп.
    
    Atomic operation для добавления групп в VkGroupsCache.
    
    Args:
        cache: VkGroupsCache instance (DI)
        groups: Список групп для добавления
    
    Returns:
        Количество добавленных групп
        
    Example:
        >>> cache = VkGroupsCache()
        >>> groups = [
        ...     {"id": 123, "name": "Tech News"},
        ...     {"id": 456, "name": "Python Tips"}
        ... ]
        >>> count = await update_cache_task(cache, groups)
        >>> count
        2
    """
    
    if not groups:
        logger.debug("No VK groups to update in cache")
        return 0
    
    count = await cache.put_groups(groups)
    
    logger.debug(f"Updated cache with {count} VK groups")
    
    return count
