"""
ValidatePostsTask: Валидация структуры постов через Pydantic.

Porto Architecture Task:
- Атомарная операция валидации
- Пропуск невалидных постов с логированием
- Использование Pydantic для валидации
"""

from typing import Dict, Any, List
import logging

from src.Containers.AppSection.TgPost.Data.PostDTO import PostDTO

logger = logging.getLogger(__name__)


async def validate_posts_task(
    raw_posts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Task: Валидировать структуру постов.
    
    Atomic operation для валидации постов через Pydantic.
    Пропускает невалидные посты с warning логированием.
    
    Args:
        raw_posts: Список raw постов из Kafka
    
    Returns:
        Список валидированных постов (пропускает невалидные)
        
    Example:
        >>> raw_posts = [
        ...     {"id": 123, "content": "Valid post"},
        ...     {"id": "invalid", "content": "Bad post"},  # будет пропущен
        ...     {"id": 124, "content": "Valid post 2"}
        ... ]
        >>> validated = await validate_posts_task(raw_posts)
        >>> len(validated)
        2
    """
    
    if not raw_posts:
        logger.debug("No posts to validate")
        return []
    
    validated = []
    
    for idx, raw_post in enumerate(raw_posts):
        try:
            # Pydantic валидация
            post_dto = PostDTO(**raw_post)
            validated.append(post_dto.model_dump())
            
        except Exception as exc:
            logger.warning(
                f"Failed to validate post at index {idx}: {exc}. Skipping."
            )
            continue
    
    logger.debug(f"Validated {len(validated)}/{len(raw_posts)} posts")
    
    return validated

