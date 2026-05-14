"""
ValidateChannelDataTask: Валидация данных канала через Pydantic.

Porto Architecture Task:
- Атомарная операция валидации канала
- Использование Pydantic ChannelDTO
"""

from typing import Dict, Any
import logging

from src.Containers.AppSection.TgPost.Data.ChannelDTO import ChannelDTO
from src.Containers.AppSection.TgPost.Exceptions.CacheValidationException import CacheValidationException

logger = logging.getLogger(__name__)


async def validate_channel_data_task(
    channel_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Task: Валидировать данные канала.
    
    Atomic operation для валидации данных канала через Pydantic ChannelDTO.
    
    Args:
        channel_data: Raw данные из Kafka
            Expected keys: id, name, type
    
    Returns:
        Валидированные данные канала
        
    Raises:
        CacheValidationException: Если данные невалидны
        
    Example:
        >>> channel_data = {"id": 123, "name": "Tech", "type": "public"}
        >>> validated = await validate_channel_data_task(channel_data)
        >>> validated["id"]
        123
    """
    
    try:
        # Pydantic валидация
        channel_dto = ChannelDTO(**channel_data)
        return channel_dto.model_dump()
        
    except Exception as exc:
        logger.error(f"Invalid channel data: {exc}")
        raise CacheValidationException(
            f"Invalid channel data: {exc}"
        )

