"""
VkGroupsCache Service: In-memory кэш для данных о VK группах.

Porto Architecture Service:
- Двухуровневая система кэширования
- Персистентный слой: синхронизация с БД при старте
- Оперативный слой: обновление через события из vk_groups_diff
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class VkGroupsCache:
    """
    Service: In-memory кэш для данных о VK группах.
    
    Двухуровневая система:
    - Персистентный слой: синхронизация с БД при старте
    - Оперативный слой: обновление через события из vk_groups_diff
    
    Паттерн: Singleton (Dishka APP scope)
    
    Workflow:
    1. Инициализация: загрузка групп из БД
    2. Runtime: обновление через события Kafka
    3. Валидация: проверка дубликатов перед созданием консьюмеров
    
    Usage:
        cache = VkGroupsCache(ttl_seconds=300)
        
        # Инициализация из БД
        await cache.put_groups(db_groups)
        
        # Проверка дубликата
        if await cache.has_group(group_id):
            logger.warning("Group already exists")
            return
        
        # Добавление новой группы
        await cache.put_groups([new_group])
        
        # Получение всех групп
        groups = await cache.get_all_groups()
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize in-memory cache for VK group objects.
        
        Args:
            ttl_seconds: Time-to-live для кэшированных объектов (по умолчанию: 300 секунд = 5 минут)
        """
        self._groups: Dict[int, Dict[str, Any]] = {}  # {group_id: group_object}
        self._ttl_seconds = ttl_seconds
        self._last_update: Optional[datetime] = None
        logger.info(f"VkGroupsCache initialized with TTL: {ttl_seconds}s")
        
    async def put_groups(self, groups: List[Dict[str, Any]]) -> int:
        """
        Put multiple VK group objects into cache.
        
        Args:
            groups: List of group dictionaries with complete data
            Expected keys: id, name, screen_name, members_count
            
        Returns:
            Number of groups added to cache
            
        Example:
            >>> cache = VkGroupsCache()
            >>> await cache.put_groups([
            ...     {"id": 123, "name": "Tech News", "screen_name": "technews"},
            ...     {"id": 456, "name": "Python Tips", "screen_name": "pythontips"}
            ... ])
            2
        """
        if not groups:
            logger.debug("No groups to put in cache")
            return 0
        
        count = 0
        for group in groups:
            raw_group_id = group.get("id")
            group_id = self._normalize_group_id(raw_group_id)
            if group_id is None:
                logger.warning(
                    f"Group without valid int id (got {raw_group_id!r}), skipping: {group}"
                )
                continue

            # Store full group object с int ключом (гарантированно int)
            group["id"] = group_id
            self._groups[group_id] = group
            count += 1
        
        self._last_update = datetime.utcnow()
        
        logger.info(f"Put {count} groups into cache (total: {len(self._groups)})")
        
        return count
    
    async def get_group(self, group_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single VK group object from cache by ID.
        
        Args:
            group_id: Group ID to retrieve
            
        Returns:
            Group object or None if not found or cache expired
            
        Example:
            >>> cache = VkGroupsCache()
            >>> await cache.put_groups([{"id": 123, "name": "Tech"}])
            >>> group = await cache.get_group(123)
            >>> group["name"]
            'Tech'
        """
        group_id = self._normalize_group_id(group_id)
        if group_id is None:
            return None

        if self._is_expired():
            logger.warning("Cache expired, clearing")
            await self.clear()
            return None

        return self._groups.get(group_id)
    
    async def has_group(self, group_id: int) -> bool:
        """
        Check if VK group exists in cache.
        
        Args:
            group_id: Group ID to check
            
        Returns:
            True if group exists in cache, False otherwise
            
        Example:
            >>> cache = VkGroupsCache()
            >>> await cache.put_groups([{"id": 123, "name": "Tech"}])
            >>> await cache.has_group(123)
            True
            >>> await cache.has_group(999)
            False
        """
        group_id = self._normalize_group_id(group_id)
        if group_id is None:
            return False

        if self._is_expired():
            logger.warning("Cache expired, clearing")
            await self.clear()
            return False

        exists = group_id in self._groups

        if exists:
            logger.debug(f"Group {group_id} exists in cache")

        return exists
    
    async def get_all_groups(self) -> List[Dict[str, Any]]:
        """
        Get all VK group objects from cache.
        
        Returns:
            List of all cached group objects
            
        Example:
            >>> cache = VkGroupsCache()
            >>> await cache.put_groups([{"id": 123}, {"id": 456}])
            >>> groups = await cache.get_all_groups()
            >>> len(groups)
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
        
        groups = list(self._groups.values())
        
        logger.debug(f"Retrieved {len(groups)} groups from cache")
        
        return groups
    
    async def clear(self) -> int:
        """
        Clear all cached VK group objects.
        
        Returns:
            Number of groups that were cleared
            
        Example:
            >>> cache = VkGroupsCache()
            >>> await cache.put_groups([{"id": 123}, {"id": 456}])
            >>> await cache.clear()
            2
            >>> await cache.get_all_groups()
            []
        """
        count = len(self._groups)
        self._groups.clear()
        self._last_update = None
        
        if count > 0:
            logger.info(f"Cleared {count} groups from cache")
        
        return count
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats:
            - total_groups: int
            - last_update: datetime | None
            - ttl_seconds: int
            - is_expired: bool
            - backend: str
            
        Example:
            >>> cache = VkGroupsCache()
            >>> stats = await cache.get_stats()
            >>> stats["backend"]
            'in-memory-objects'
        """
        return {
            "total_groups": len(self._groups),
            "last_update": self._last_update,
            "ttl_seconds": self._ttl_seconds,
            "is_expired": self._is_expired(),
            "backend": "in-memory-objects"
        }
    
    async def size(self) -> int:
        """
        Get current cache size.
        
        Returns:
            Number of cached groups
            
        Example:
            >>> cache = VkGroupsCache()
            >>> await cache.put_groups([{"id": 123}])
            >>> await cache.size()
            1
        """
        return len(self._groups)
    
    @staticmethod
    def _normalize_group_id(group_id: Any) -> Optional[int]:
        """
        Coerce an externally provided group_id to ``int``.

        Prevents an int-vs-str split-brain where the same VK group would be
        registered under two different dict keys (e.g. ``29534144`` and
        ``"29534144"``), which in turn caused duplicate AIOKafkaConsumer
        instances to join the same Kafka consumer group and trigger a
        constant rebalance loop.
        """
        if group_id is None:
            return None
        try:
            return int(group_id)
        except (TypeError, ValueError):
            return None

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
