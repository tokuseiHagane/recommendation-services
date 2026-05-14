from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GroupObjectsCache:
    """
    In-memory cache manager for full VK group objects.
    
    Purpose:
    - Store complete group objects (not just IDs) after upsert
    - Serve as intermediate storage before publishing to Kafka
    - Enable batch publishing from cache
    
    Workflow:
    1. Batch upsert groups to DB
    2. Put all upserted groups into cache
    3. Read groups from cache
    4. Publish to Kafka topic vk_groups_diff
    5. Clear cache after successful publish
    
    Usage:
        cache = GroupObjectsCache()
        
        # After upsert
        await cache.put_groups(upserted_groups)
        
        # Read and publish
        groups = await cache.get_all_groups()
        await publish_to_kafka(groups)
        
        # Clear after publish
        await cache.clear()
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize in-memory cache for group objects.
        
        Args:
            ttl_seconds: Time-to-live for cached objects (default: 300 seconds = 5 minutes)
        """
        self._groups: Dict[int, Dict[str, Any]] = {}  # {group_id: group_object}
        self._ttl_seconds = ttl_seconds
        self._last_update: Optional[datetime] = None
        
    async def put_groups(self, groups: List[Dict[str, Any]]) -> int:
        """
        Put multiple group objects into cache.
        
        Args:
            groups: List of group dictionaries with complete data
            
        Returns:
            Number of groups added to cache
        """
        if not groups:
            logger.debug("No groups to put in cache")
            return 0
        
        count = 0
        for group in groups:
            group_id = group.get("id")
            if group_id is None:
                logger.warning(f"Group without id, skipping: {group}")
                continue
                
            # Store full group object (using int key)
            self._groups[int(group_id)] = group
            count += 1
        
        self._last_update = datetime.utcnow()
        
        logger.info(f"Put {count} VK groups into cache (total: {len(self._groups)})")
        
        return count
    
    async def get_all_groups(self) -> List[Dict[str, Any]]:
        """
        Get all group objects from cache.
        
        Returns:
            List of all cached group objects
        """
        # Check TTL
        if self._last_update and self._is_expired():
            logger.warning(
                f"VK groups cache expired (TTL: {self._ttl_seconds}s), "
                f"last update: {self._last_update}"
            )
            await self.clear()
            return []
        
        groups = list(self._groups.values())
        
        logger.debug(f"Retrieved {len(groups)} VK groups from cache")
        
        return groups
    
    async def get_group(self, group_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single group object from cache by ID.
        
        Args:
            group_id: Group ID to retrieve
            
        Returns:
            Group object or None if not found
        """
        if self._is_expired():
            logger.warning("VK groups cache expired, clearing")
            await self.clear()
            return None
            
        return self._groups.get(int(group_id))
    
    async def clear(self) -> int:
        """
        Clear all cached group objects.
        
        Returns:
            Number of groups that were cleared
        """
        count = len(self._groups)
        self._groups.clear()
        self._last_update = None
        
        if count > 0:
            logger.info(f"Cleared {count} VK groups from cache")
        
        return count
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            "total_groups": len(self._groups),
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
            Number of cached groups
        """
        return len(self._groups)


# Singleton instance
_objects_cache_instance: Optional[GroupObjectsCache] = None


def get_group_objects_cache() -> GroupObjectsCache:
    """
    Get the singleton GroupObjectsCache instance.
    
    Returns:
        GroupObjectsCache instance
    """
    global _objects_cache_instance
    if _objects_cache_instance is None:
        _objects_cache_instance = GroupObjectsCache()
    return _objects_cache_instance


async def close_group_objects_cache():
    """
    Close/cleanup the objects cache.
    """
    global _objects_cache_instance
    if _objects_cache_instance:
        await _objects_cache_instance.clear()
        _objects_cache_instance = None
        logger.info("VK group objects cache closed")
