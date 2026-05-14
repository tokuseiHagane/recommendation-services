"""
BatchUpsertPostsTask: Batch INSERT ON CONFLICT UPDATE постов в БД.

Porto Architecture Task:
- Атомарная операция для batch upsert
- Дедупликация по id
- Идемпотентность через ON CONFLICT UPDATE
"""

from typing import Dict, Any, List
import logging

from src.Containers.AppSection.TgPost.Models.Post import Post
from src.Containers.AppSection.TgPost.Exceptions.BatchUpsertException import BatchUpsertException

logger = logging.getLogger(__name__)


async def batch_upsert_posts_task(
    posts: List[Dict[str, Any]]
) -> int:
    """
    Task: Batch upsert постов с идемпотентностью.
    
    Atomic operation для вставки батча постов с обработкой конфликтов.
    Использует INSERT ON CONFLICT UPDATE для идемпотентности.
    
    Args:
        posts: Список валидированных постов (dict representation)
    
    Returns:
        Количество upserted постов
        
    Raises:
        BatchUpsertException: Если batch upsert провалился
        
    Example:
        >>> posts = [
        ...     {"id": 123, "content": "Post 1", "id_channels": 456},
        ...     {"id": 124, "content": "Post 2", "id_channels": 456}
        ... ]
        >>> count = await batch_upsert_posts_task(posts)
        >>> count
        2
    """
    
    if not posts:
        logger.warning("Attempted batch upsert with empty posts list")
        return 0
    
    try:
        # Дедупликация по id (берем последний)
        unique_posts = {}
        for post in posts:
            post_id = post.get("id")
            if post_id:
                unique_posts[post_id] = post
        
        if not unique_posts:
            logger.warning("No valid posts with id after deduplication")
            return 0
        
        # Создать Post instances
        post_rows = [
            Post(
                id=p["id"],
                content=p.get("content"),
                repost_count=p.get("repost_count", 0),
                view_count=p.get("view_count", 0),
                link=p.get("link"),
                message_timestamp=p.get("message_timestamp"),
                has_reactions=p.get("has_reactions", False),
                id_channels=p.get("id_channels"),
                free_reactions_count=p.get("free_reactions_count", 0),
                paid_reactions_count=p.get("paid_reactions_count", 0),
            )
            for p in unique_posts.values()
        ]
        
        # Batch upsert с ON CONFLICT UPDATE
        # Piccolo syntax: .on_conflict(action="DO UPDATE", target=column, values=[...])
        await Post.insert(*post_rows).on_conflict(
            action="DO UPDATE",
            target=Post.id,
            values=[
                Post.content,
                Post.repost_count,
                Post.view_count,
                Post.link,
                Post.message_timestamp,
                Post.has_reactions,
                Post.id_channels,
                Post.free_reactions_count,
                Post.paid_reactions_count,
            ]
        )
        
        logger.info(f"Successfully upserted {len(post_rows)} posts")
        
        return len(post_rows)
        
    except Exception as exc:
        logger.exception(f"Failed to batch upsert {len(posts)} posts: {exc}")
        raise BatchUpsertException(f"Batch upsert failed: {exc}")

