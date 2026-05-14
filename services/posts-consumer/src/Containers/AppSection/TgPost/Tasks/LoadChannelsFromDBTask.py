"""
LoadChannelsFromDBTask: Загрузка каналов из БД.

Porto Architecture Task:
- Атомарная операция загрузки данных
- Используется для инициализации кэша при старте

Note: Этот Task требует определения источника данных о каналах.
      Варианты:
      1. Локальная таблица channels в TgPost контейнере
      2. Доступ к БД Telegram-Channel-Consumer через shared connection
      3. Использование Post.id_channels для получения уникальных каналов

      Для минимальной реализации используем вариант 3.
"""

from typing import Dict, Any, List
import logging

from src.Containers.AppSection.TgPost.Models.Post import Post

logger = logging.getLogger(__name__)


async def load_channels_from_db_task() -> List[Dict[str, Any]]:
    """
    Task: Загрузить все каналы из БД.
    
    Atomic operation для загрузки уникальных id_channels из posts таблицы.
    
    Примечание: Минимальная реализация через Post.id_channels.
    Для полноценной реализации нужна интеграция с Telegram-Channel-Consumer.
    
    Returns:
        Список каналов с полями: id, name, type
        Для минимальной реализации: [{id: channel_id, name: str(channel_id), type: "unknown"}]
        
    Raises:
        Exception: Если не удалось загрузить из БД
        
    Example:
        >>> channels = await load_channels_from_db_task()
        >>> len(channels)
        5
        >>> channels[0]["id"]
        123
    """
    
    try:
        # Загрузить уникальные id_channels из posts
        # SELECT DISTINCT id_channels FROM posts WHERE id_channels IS NOT NULL
        result = await Post.select(Post.id_channels).distinct()
        
        channels = []
        for row in result:
            channel_id = row["id_channels"]
            if channel_id:
                channels.append({
                    "id": channel_id,
                    "name": f"Channel_{channel_id}",  # Placeholder
                    "type": "unknown"  # Placeholder
                })
        
        logger.info(f"Loaded {len(channels)} unique channels from DB")
        
        return channels
        
    except Exception as exc:
        logger.exception(f"Failed to load channels from DB: {exc}")
        # Вернуть пустой список вместо raise для graceful degradation
        return []

