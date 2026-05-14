"""
ValidateVkPostsTask: Валидация структуры VK постов через Pydantic.

Porto Architecture Task:
- Атомарная операция валидации
- Пропуск невалидных постов с логированием
- Использование Pydantic для валидации
"""

from typing import Dict, Any, List
import logging

from src.Containers.AppSection.VkPost.Data.VkPostDTO import VkPostDTO

logger = logging.getLogger(__name__)


async def validate_vk_posts_task(
    raw_posts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Task: Валидировать структуру VK постов.
    
    Atomic operation для валидации VK постов через Pydantic.
    Пропускает невалидные посты с warning логированием.
    
    Args:
        raw_posts: Список raw VK постов из Kafka
    
    Returns:
        Список валидированных постов (пропускает невалидные)
        
    Example:
        >>> raw_posts = [
        ...     {"id": 123, "len_message": 100},
        ...     {"id": "invalid", "len_message": 50},  # будет пропущен
        ...     {"id": 124, "len_message": 200}
        ... ]
        >>> validated = await validate_vk_posts_task(raw_posts)
        >>> len(validated)
        2
    """
    
    if not raw_posts:
        logger.debug("No VK posts to validate")
        return []
    
    validated = []
    
    for idx, raw_post in enumerate(raw_posts):
        try:
            # Pydantic валидация
            post_dto = VkPostDTO(**raw_post)
            validated.append(post_dto.model_dump())
            
        except Exception as exc:
            logger.warning(
                f"Failed to validate VK post at index {idx}: {exc}. Skipping."
            )
            continue
    
    logger.debug(f"Validated {len(validated)}/{len(raw_posts)} VK posts")
    
    return validated
