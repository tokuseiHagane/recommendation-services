"""
BatchUpsertVkPostsTask: Batch INSERT ON CONFLICT UPDATE VK постов в БД.

Porto Architecture Task:
- Атомарная операция для batch upsert
- Дедупликация по id
- Идемпотентность через ON CONFLICT UPDATE
"""

from typing import Dict, Any, List
import logging

from src.Containers.AppSection.VkPost.Models.VkPost import VkPost
from src.Containers.AppSection.VkPost.Exceptions.BatchUpsertException import BatchUpsertException

logger = logging.getLogger(__name__)


async def batch_upsert_vk_posts_task(
    posts: List[Dict[str, Any]]
) -> int:
    """
    Task: Batch upsert VK постов с идемпотентностью.
    
    Atomic operation для вставки батча VK постов с обработкой конфликтов.
    Использует INSERT ON CONFLICT UPDATE для идемпотентности.
    
    Args:
        posts: Список валидированных VK постов (dict representation)
    
    Returns:
        Количество upserted постов
        
    Raises:
        BatchUpsertException: Если batch upsert провалился
        
    Example:
        >>> posts = [
        ...     {"id": 123, "len_message": 100, "id_groups": 456},
        ...     {"id": 124, "len_message": 200, "id_groups": 456}
        ... ]
        >>> count = await batch_upsert_vk_posts_task(posts)
        >>> count
        2
    """
    
    if not posts:
        logger.warning("Attempted batch upsert with empty VK posts list")
        return 0
    
    try:
        # Дедупликация по id (берем последний)
        unique_posts = {}
        for post in posts:
            post_id = post.get("id")
            if post_id:
                unique_posts[post_id] = post
        
        if not unique_posts:
            logger.warning("No valid VK posts with id after deduplication")
            return 0
        
        # Создать VkPost instances
        post_rows = [
            VkPost(
                id=p["id"],
                len_message=p.get("len_message"),
                repost_count=p.get("repost_count", 0),
                view_count=p.get("view_count", 0),
                comments_count=p.get("comments_count", 0),
                message_timestamp=p.get("message_timestamp"),
                edit_date=p.get("edit_date"),
                reactions_count=p.get("reactions_count", 0),
                id_groups=p.get("id_groups"),
            )
            for p in unique_posts.values()
        ]
        
        # Batch upsert с ON CONFLICT UPDATE
        await VkPost.insert(*post_rows).on_conflict(
            action="DO UPDATE",
            target=VkPost.id,
            values=[
                VkPost.len_message,
                VkPost.repost_count,
                VkPost.view_count,
                VkPost.comments_count,
                VkPost.message_timestamp,
                VkPost.edit_date,
                VkPost.reactions_count,
                VkPost.id_groups,
            ]
        )
        
        logger.info(f"Successfully upserted {len(post_rows)} VK posts")
        
        return len(post_rows)
        
    except Exception as exc:
        logger.exception(f"Failed to batch upsert {len(posts)} VK posts: {exc}")
        raise BatchUpsertException(f"VK Batch upsert failed: {exc}")
