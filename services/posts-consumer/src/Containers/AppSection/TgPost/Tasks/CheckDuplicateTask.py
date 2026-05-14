"""
CheckDuplicateTask: Проверка дубликатов в кэше.

Porto Architecture Task:
- Атомарная операция проверки наличия
- Делегирует к PostObjectsCache.has_channel()
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def check_duplicate_task(
    cache: Any,  # PostObjectsCache
    channel_id: int
) -> bool:
    """
    Task: Проверить наличие канала в кэше.
    
    Atomic operation для проверки дубликатов через PostObjectsCache.
    
    Args:
        cache: PostObjectsCache instance (DI)
        channel_id: ID канала для проверки
    
    Returns:
        True если канал уже существует, False если нет
        
    Example:
        >>> cache = PostObjectsCache()
        >>> await cache.put_channels([{"id": 123, "name": "Tech"}])
        >>> exists = await check_duplicate_task(cache, 123)
        >>> exists
        True
        >>> exists = await check_duplicate_task(cache, 999)
        >>> exists
        False
    """
    
    exists = await cache.has_channel(channel_id)
    
    if exists:
        logger.debug(f"Channel {channel_id} already exists in cache")
    
    return exists

