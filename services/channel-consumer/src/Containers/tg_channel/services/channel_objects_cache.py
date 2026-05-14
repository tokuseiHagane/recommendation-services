from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ChannelObjectsCache:
    """
    In-memory cache manager for full Telegram channel objects.
    
    Purpose:
    - Store complete channel objects (not just IDs) after upsert
    - Serve as intermediate storage before publishing to Kafka
    - Enable batch publishing from cache
    
    Workflow:
    1. Batch upsert channels to DB
    2. Put all upserted channels into cache
    3. Read channels from cache
    4. Publish to Kafka topic tg_channels_diff
    5. Clear cache after successful publish
    
    Usage:
        cache = ChannelObjectsCache()
        
        # After upsert
        await cache.put_channels(upserted_channels)
        
        # Read and publish
        channels = await cache.get_all_channels()
        await publish_to_kafka(channels)
        
        # Clear after publish
        await cache.clear()
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize in-memory cache for channel objects.
        
        Args:
            ttl_seconds: Time-to-live for cached objects (default: 300 seconds = 5 minutes)
        """
        self._channels: Dict[str, Dict[str, Any]] = {}  # {channel_id: channel_object}
        self._ttl_seconds = ttl_seconds
        self._last_update: Optional[datetime] = None
        
    async def put_channels(self, channels: List[Dict[str, Any]]) -> int:
        """
        Put multiple channel objects into cache.
        
        Args:
            channels: List of channel dictionaries with complete data
            
        Returns:
            Number of channels added to cache
        """
        if not channels:
            logger.debug("No channels to put in cache")
            return 0
        
        count = 0
        for channel in channels:
            channel_id = channel.get("id")
            if channel_id is None:
                logger.warning(f"Channel without id, skipping: {channel}")
                continue
                
            # Store full channel object
            self._channels[str(channel_id)] = channel
            count += 1
        
        self._last_update = datetime.utcnow()
        
        logger.info(f"Put {count} channels into cache (total: {len(self._channels)})")
        
        return count
    
    async def get_all_channels(self) -> List[Dict[str, Any]]:
        """
        Get all channel objects from cache.
        
        Returns:
            List of all cached channel objects
        """
        # Check TTL
        if self._last_update and self._is_expired():
            logger.warning(
                f"Cache expired (TTL: {self._ttl_seconds}s), "
                f"last update: {self._last_update}"
            )
            await self.clear()
            return []
        
        channels = list(self._channels.values())
        
        logger.debug(f"Retrieved {len(channels)} channels from cache")
        
        return channels
    
    async def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single channel object from cache by ID.
        
        Args:
            channel_id: Channel ID to retrieve
            
        Returns:
            Channel object or None if not found
        """
        if self._is_expired():
            logger.warning("Cache expired, clearing")
            await self.clear()
            return None
            
        return self._channels.get(str(channel_id))
    
    async def clear(self) -> int:
        """
        Clear all cached channel objects.
        
        Returns:
            Number of channels that were cleared
        """
        count = len(self._channels)
        self._channels.clear()
        self._last_update = None
        
        if count > 0:
            logger.info(f"Cleared {count} channels from cache")
        
        return count
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            "total_channels": len(self._channels),
            "last_update": self._last_update,
            "ttl_seconds": self._ttl_seconds,
            "is_expired": self._is_expired(),
            "backend": "in-memory-objects"
        }
    
    def _is_expired(self) -> bool:
        """
        Check if cache has expired based on TTL.
        
        Returns:
            True if cache is expired, False otherwise
        """
        if self._last_update is None:
            return False
            
        elapsed = datetime.utcnow() - self._last_update
        return elapsed > timedelta(seconds=self._ttl_seconds)
    
    async def size(self) -> int:
        """
        Get current cache size.
        
        Returns:
            Number of cached channels
        """
        return len(self._channels)


# Singleton instance
_objects_cache_instance: Optional[ChannelObjectsCache] = None


def get_channel_objects_cache() -> ChannelObjectsCache:
    """
    Get the singleton ChannelObjectsCache instance.
    
    Returns:
        ChannelObjectsCache instance
    """
    global _objects_cache_instance
    if _objects_cache_instance is None:
        _objects_cache_instance = ChannelObjectsCache()
    return _objects_cache_instance


async def close_channel_objects_cache():
    """
    Close/cleanup the objects cache.
    """
    global _objects_cache_instance
    if _objects_cache_instance:
        await _objects_cache_instance.clear()
        _objects_cache_instance = None
        logger.info("Channel objects cache closed")

