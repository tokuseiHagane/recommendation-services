"""
PostObjectsCache Service: In-memory кэш для данных о каналах.

Porto Architecture Service:
- Двухуровневая система кэширования
- Персистентный слой: синхронизация с БД при старте
- Оперативный слой: обновление через события из tg_channels_diff
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PostObjectsCache:
    """
    Service: In-memory кэш для данных о каналах.
    
    Двухуровневая система:
    - Персистентный слой: синхронизация с БД при старте
    - Оперативный слой: обновление через события из tg_channels_diff
    
    Паттерн: Singleton (Dishka APP scope)
    
    Workflow:
    1. Инициализация: загрузка каналов из БД
    2. Runtime: обновление через события Kafka
    3. Валидация: проверка дубликатов перед созданием консьюмеров
    
    Usage:
        cache = PostObjectsCache(ttl_seconds=300)
        
        # Инициализация из БД
        await cache.put_channels(db_channels)
        
        # Проверка дубликата
        if await cache.has_channel(channel_id):
            logger.warning("Channel already exists")
            return
        
        # Добавление нового канала
        await cache.put_channels([new_channel])
        
        # Получение всех каналов
        channels = await cache.get_all_channels()
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize in-memory cache for channel objects.
        
        Args:
            ttl_seconds: Time-to-live для кэшированных объектов (по умолчанию: 300 секунд = 5 минут)
        """
        self._channels: Dict[int, Dict[str, Any]] = {}  # {channel_id: channel_object}
        self._ttl_seconds = ttl_seconds
        self._last_update: Optional[datetime] = None
        logger.info(f"PostObjectsCache initialized with TTL: {ttl_seconds}s")
        
    async def put_channels(self, channels: List[Dict[str, Any]]) -> int:
        """
        Put multiple channel objects into cache.
        
        Args:
            channels: List of channel dictionaries with complete data
            Expected keys: id, name, type
            
        Returns:
            Number of channels added to cache
            
        Example:
            >>> cache = PostObjectsCache()
            >>> await cache.put_channels([
            ...     {"id": 123, "name": "Tech News", "type": "public"},
            ...     {"id": 456, "name": "Python Tips", "type": "private"}
            ... ])
            2
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
                
            # Store full channel object с int ключом
            self._channels[channel_id] = channel
            count += 1
        
        self._last_update = datetime.utcnow()
        
        logger.info(f"Put {count} channels into cache (total: {len(self._channels)})")
        
        return count
    
    async def get_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single channel object from cache by ID.
        
        Args:
            channel_id: Channel ID to retrieve
            
        Returns:
            Channel object or None if not found or cache expired
            
        Example:
            >>> cache = PostObjectsCache()
            >>> await cache.put_channels([{"id": 123, "name": "Tech"}])
            >>> channel = await cache.get_channel(123)
            >>> channel["name"]
            'Tech'
        """
        if self._is_expired():
            logger.warning("Cache expired, clearing")
            await self.clear()
            return None
            
        return self._channels.get(channel_id)
    
    async def has_channel(self, channel_id: int) -> bool:
        """
        Check if channel exists in cache.
        
        Args:
            channel_id: Channel ID to check
            
        Returns:
            True if channel exists in cache, False otherwise
            
        Example:
            >>> cache = PostObjectsCache()
            >>> await cache.put_channels([{"id": 123, "name": "Tech"}])
            >>> await cache.has_channel(123)
            True
            >>> await cache.has_channel(999)
            False
        """
        if self._is_expired():
            logger.warning("Cache expired, clearing")
            await self.clear()
            return False
            
        exists = channel_id in self._channels
        
        if exists:
            logger.debug(f"Channel {channel_id} exists in cache")
        
        return exists
    
    async def get_all_channels(self) -> List[Dict[str, Any]]:
        """
        Get all channel objects from cache.
        
        Returns:
            List of all cached channel objects
            
        Example:
            >>> cache = PostObjectsCache()
            >>> await cache.put_channels([{"id": 123}, {"id": 456}])
            >>> channels = await cache.get_all_channels()
            >>> len(channels)
            2
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
    
    async def clear(self) -> int:
        """
        Clear all cached channel objects.
        
        Returns:
            Number of channels that were cleared
            
        Example:
            >>> cache = PostObjectsCache()
            >>> await cache.put_channels([{"id": 123}, {"id": 456}])
            >>> await cache.clear()
            2
            >>> await cache.get_all_channels()
            []
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
            Dictionary with cache stats:
            - total_channels: int
            - last_update: datetime | None
            - ttl_seconds: int
            - is_expired: bool
            - backend: str
            
        Example:
            >>> cache = PostObjectsCache()
            >>> stats = await cache.get_stats()
            >>> stats["backend"]
            'in-memory-objects'
        """
        return {
            "total_channels": len(self._channels),
            "last_update": self._last_update,
            "ttl_seconds": self._ttl_seconds,
            "is_expired": self._is_expired(),
            "backend": "in-memory-objects"
        }
    
    async def size(self) -> int:
        """
        Get current cache size.
        
        Returns:
            Number of cached channels
            
        Example:
            >>> cache = PostObjectsCache()
            >>> await cache.put_channels([{"id": 123}])
            >>> await cache.size()
            1
        """
        return len(self._channels)
    
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

