"""
VkPost Model: Представляет пост из VK группы.

Схема соответствует SQL определению из vk_db.sql.
ON CONFLICT UPDATE паттерн для идемпотентности.
"""

from piccolo.table import Table
from piccolo.columns import (
    Integer,
    Timestamptz,
)
from piccolo.columns.defaults.timestamptz import TimestamptzNow


class VkPost(Table, tablename="posts"):
    """
    Porto Model: VK post entity.
    
    Schema aligned with VKParserService `posts` table.
    
    Attributes:
        id: Unique post identifier (primary key)
        len_message: Length of post message
        repost_count: Number of reposts
        view_count: Number of views
        comments_count: Number of comments
        message_timestamp: Post publication timestamp
        edit_date: Post edit timestamp
        reactions_count: Total reactions count
        id_groups: Foreign key to VK group
        cached_at: Timestamp maintained by cache write path
    
    Indexes:
        - PRIMARY KEY on id
        - idx_vk_posts_id_groups on id_groups (created in migration)
        - idx_vk_posts_timestamp on message_timestamp (created in migration)
    
    Relationships:
        - id_groups → groups.id (VkGroup model)
    
    ON CONFLICT behavior:
        - ON CONFLICT (id) DO UPDATE SET ... (idempotent upserts)
    
    Example usage:
        # Single insert
        post = VkPost(id=123, len_message=100, id_groups=456)
        await post.save()
        
        # Batch upsert with ON CONFLICT UPDATE
        posts = [VkPost(id=1, len_message=50), VkPost(id=2, len_message=100)]
        await VkPost.insert(*posts).on_conflict(
            action="DO UPDATE",
            target=VkPost.id,
            values=[VkPost.len_message, VkPost.view_count, ...]
        )
    """
    
    id = Integer(
        primary_key=True,
        help_text="Unique post identifier"
    )
    
    len_message = Integer(
        null=True,
        help_text="Length of post message"
    )
    
    repost_count = Integer(
        null=True,
        default=0,
        help_text="Number of reposts"
    )
    
    view_count = Integer(
        null=True,
        default=0,
        help_text="Number of views"
    )
    
    comments_count = Integer(
        null=True,
        default=0,
        help_text="Number of comments"
    )
    
    message_timestamp = Timestamptz(
        null=True,
        help_text="Post publication timestamp"
    )
    
    edit_date = Timestamptz(
        null=True,
        help_text="Post edit timestamp"
    )
    
    reactions_count = Integer(
        null=True,
        default=0,
        help_text="Total reactions count"
    )
    
    id_groups = Integer(
        null=True,
        index=True,
        help_text="Foreign key to VK group"
    )

    cached_at = Timestamptz(
        default=TimestamptzNow(),
        help_text="When this post was cached"
    )
