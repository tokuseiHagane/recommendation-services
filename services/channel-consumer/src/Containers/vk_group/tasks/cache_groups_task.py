from typing import List, Dict, Any
import logging
from src.Containers.vk_group.services.group_objects_cache import get_group_objects_cache

logger = logging.getLogger(__name__)


async def cache_groups_task(groups: List[Dict[str, Any]]) -> int:
    """
    Atomic task: Put VK group objects into cache after upsert.
    
    This task stores complete group objects (not just IDs) in in-memory cache
    to serve as intermediate storage before publishing to Kafka.
    
    Workflow:
    1. Groups are upserted to database
    2. This task puts them into cache
    3. Later, publish_from_cache_task reads and publishes to Kafka
    
    Args:
        groups: List of group dictionaries with complete data
        
    Returns:
        Number of groups successfully cached
        
    Raises:
        Exception: If caching fails
    """
    if not groups:
        logger.debug("No VK groups to cache")
        return 0
    
    try:
        cache = get_group_objects_cache()
        
        cached_count = await cache.put_groups(groups)
        
        logger.info(f"Cached {cached_count} VK groups after upsert")
        
        return cached_count
        
    except Exception as exc:
        logger.exception(f"Failed to cache {len(groups)} VK groups: {exc}")
        raise


async def get_cached_groups_task() -> List[Dict[str, Any]]:
    """
    Atomic task: Retrieve all VK group objects from cache.
    
    Returns:
        List of cached group objects
        
    Raises:
        Exception: If retrieval fails
    """
    try:
        cache = get_group_objects_cache()
        
        groups = await cache.get_all_groups()
        
        logger.debug(f"Retrieved {len(groups)} VK groups from cache")
        
        return groups
        
    except Exception as exc:
        logger.exception(f"Failed to get VK groups from cache: {exc}")
        raise


async def clear_cache_task() -> int:
    """
    Atomic task: Clear all cached VK group objects.
    
    Should be called after successful publishing to Kafka.
    
    Returns:
        Number of groups cleared from cache
        
    Raises:
        Exception: If clearing fails
    """
    try:
        cache = get_group_objects_cache()
        
        cleared_count = await cache.clear()
        
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} VK groups from cache")
        
        return cleared_count
        
    except Exception as exc:
        logger.exception(f"Failed to clear VK groups cache: {exc}")
        raise
