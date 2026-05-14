from typing import List, Dict, Any
import logging
from src.Containers.tg_channel.services.channel_objects_cache import get_channel_objects_cache

logger = logging.getLogger(__name__)


async def cache_channels_task(channels: List[Dict[str, Any]]) -> int:
    """
    Atomic task: Put channel objects into cache after upsert.
    
    This task stores complete channel objects (not just IDs) in in-memory cache
    to serve as intermediate storage before publishing to Kafka.
    
    Workflow:
    1. Channels are upserted to database
    2. This task puts them into cache
    3. Later, publish_from_cache_task reads and publishes to Kafka
    
    Args:
        channels: List of channel dictionaries with complete data
        
    Returns:
        Number of channels successfully cached
        
    Raises:
        Exception: If caching fails
    """
    if not channels:
        logger.debug("No channels to cache")
        return 0
    
    try:
        cache = get_channel_objects_cache()
        
        cached_count = await cache.put_channels(channels)
        
        logger.info(f"Cached {cached_count} channels after upsert")
        
        return cached_count
        
    except Exception as exc:
        logger.exception(f"Failed to cache {len(channels)} channels: {exc}")
        raise


async def get_cached_channels_task() -> List[Dict[str, Any]]:
    """
    Atomic task: Retrieve all channel objects from cache.
    
    Returns:
        List of cached channel objects
        
    Raises:
        Exception: If retrieval fails
    """
    try:
        cache = get_channel_objects_cache()
        
        channels = await cache.get_all_channels()
        
        logger.debug(f"Retrieved {len(channels)} channels from cache")
        
        return channels
        
    except Exception as exc:
        logger.exception(f"Failed to get channels from cache: {exc}")
        raise


async def clear_cache_task() -> int:
    """
    Atomic task: Clear all cached channel objects.
    
    Should be called after successful publishing to Kafka.
    
    Returns:
        Number of channels cleared from cache
        
    Raises:
        Exception: If clearing fails
    """
    try:
        cache = get_channel_objects_cache()
        
        cleared_count = await cache.clear()
        
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} channels from cache")
        
        return cleared_count
        
    except Exception as exc:
        logger.exception(f"Failed to clear cache: {exc}")
        raise

