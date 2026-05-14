"""
CheckDuplicateTask: Проверка дубликатов VK групп в кэше.

Porto Architecture Task:
- Атомарная операция проверки наличия
- Делегирует к VkGroupsCache.has_group()
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def check_duplicate_task(
    cache: Any,  # VkGroupsCache
    group_id: int
) -> bool:
    """
    Task: Проверить наличие VK группы в кэше.
    
    Atomic operation для проверки дубликатов через VkGroupsCache.
    
    Args:
        cache: VkGroupsCache instance (DI)
        group_id: ID VK группы для проверки
    
    Returns:
        True если группа уже существует, False если нет
        
    Example:
        >>> cache = VkGroupsCache()
        >>> await cache.put_groups([{"id": 123, "name": "Tech"}])
        >>> exists = await check_duplicate_task(cache, 123)
        >>> exists
        True
        >>> exists = await check_duplicate_task(cache, 999)
        >>> exists
        False
    """
    
    exists = await cache.has_group(group_id)
    
    if exists:
        logger.debug(f"VK Group {group_id} already exists in cache")
    
    return exists
