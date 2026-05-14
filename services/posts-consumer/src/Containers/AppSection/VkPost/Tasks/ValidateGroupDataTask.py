"""
ValidateGroupDataTask: Валидация данных VK группы.

Porto Architecture Task:
- Атомарная операция валидации
- Использование Pydantic для валидации
"""

from typing import Dict, Any, Optional
import logging

from src.Containers.AppSection.VkPost.Data.GroupDTO import GroupDTO
from src.Containers.AppSection.VkPost.Exceptions.CacheValidationException import CacheValidationException

logger = logging.getLogger(__name__)


async def validate_group_data_task(
    raw_group: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Task: Валидировать данные VK группы.
    
    Atomic operation для валидации группы через Pydantic.
    
    Args:
        raw_group: Raw данные группы из Kafka
    
    Returns:
        Валидированный dict или None если невалидный
        
    Raises:
        CacheValidationException: Если валидация провалилась
        
    Example:
        >>> raw = {"id": 123, "name": "Tech News", "screen_name": "technews"}
        >>> validated = await validate_group_data_task(raw)
        >>> validated["id"]
        123
    """
    
    if not raw_group:
        logger.warning("Empty group data received")
        return None
    
    try:
        group_dto = GroupDTO(**raw_group)
        validated = group_dto.model_dump()
        
        logger.debug(f"Validated VK group: {validated.get('id')}")
        
        return validated
        
    except Exception as exc:
        logger.warning(f"Failed to validate VK group data: {exc}")
        raise CacheValidationException(f"VK Group validation failed: {exc}")
