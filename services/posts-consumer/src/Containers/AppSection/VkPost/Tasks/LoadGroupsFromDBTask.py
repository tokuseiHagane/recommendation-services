"""
LoadGroupsFromDBTask: Загрузка VK групп из БД.

Porto Architecture Task:
- Атомарная операция загрузки данных
- Используется для инициализации кэша при старте
"""

from typing import Dict, Any, List
import logging

from src.Containers.AppSection.VkPost.Models.VkPost import VkPost
from src.Containers.AppSection.VkPost.Models.VkGroup import VkGroup

logger = logging.getLogger(__name__)


async def load_groups_from_db_task() -> List[Dict[str, Any]]:
    """
    Task: Загрузить все VK группы из БД.
    
    Atomic operation для загрузки VK групп.
    Сначала пытается загрузить из таблицы groups,
    если не удалось - загружает уникальные id_groups из posts.
    
    Returns:
        Список групп с полями: id, name, screen_name, members_count
        
    Raises:
        Exception: Если не удалось загрузить из БД
        
    Example:
        >>> groups = await load_groups_from_db_task()
        >>> len(groups)
        5
        >>> groups[0]["id"]
        123
    """
    
    try:
        # Попытка загрузить из таблицы groups
        groups_result = await VkGroup.select()
        
        if groups_result:
            groups = [
                {
                    "id": row["id"],
                    "name": row.get("name", f"Group_{row['id']}"),
                    "screen_name": row.get("screen_name"),
                    "members_count": row.get("members_count"),
                }
                for row in groups_result
            ]
            logger.info(f"Loaded {len(groups)} VK groups from groups table")
            return groups
        
        # Fallback: загрузить уникальные id_groups из posts
        result = await VkPost.select(VkPost.id_groups).distinct()
        
        groups = []
        for row in result:
            group_id = row["id_groups"]
            if group_id:
                groups.append({
                    "id": group_id,
                    "name": f"VkGroup_{group_id}",  # Placeholder
                    "screen_name": None,
                    "members_count": None,
                })
        
        logger.info(f"Loaded {len(groups)} unique VK groups from posts table")
        
        return groups
        
    except Exception as exc:
        logger.exception(f"Failed to load VK groups from DB: {exc}")
        # Вернуть пустой список вместо raise для graceful degradation
        return []
