"""
Post Model: Представляет пост из Telegram канала.

Схема соответствует SQL определению из post_model.md.
ON CONFLICT UPDATE паттерн для идемпотентности.
"""

from piccolo.table import Table
from piccolo.columns import (
    Integer,
    Text,
    Boolean,
    Timestamp,
    JSONB
)


class Post(Table, tablename="posts"):
    """
    Porto Model: Telegram post entity.
    
    Attributes:
        id: Unique post identifier (primary key)
        content: Post text content
        repost_count: Number of reposts
        view_count: Number of views
        link: JSONB structure with links
        message_timestamp: Post publication timestamp
        has_reactions: Whether post has reactions
        id_channels: Foreign key to channel (external microservice)
        free_reactions_count: Count of free reactions
        paid_reactions_count: Count of paid reactions
    
    Indexes:
        - PRIMARY KEY on id
        - idx_posts_id_channels on id_channels (created in migration)
        - idx_posts_timestamp on message_timestamp (created in migration)
    
    Relationships:
        - id_channels → channels.id (external microservice, soft reference)
    
    ON CONFLICT behavior:
        - ON CONFLICT (id) DO UPDATE SET ... (idempotent upserts)
    
    Example usage:
        # Single insert
        post = Post(id=123, content="Test", id_channels=456)
        await post.save()
        
        # Batch upsert with ON CONFLICT UPDATE
        posts = [Post(id=1, content="Post 1"), Post(id=2, content="Post 2")]
        await Post.insert(*posts).on_conflict(
            action="DO UPDATE",
            target=Post.id,
            values=[Post.content, Post.view_count, ...]
        )
    """
    
    id = Integer(
        primary_key=True,
        help_text="Unique post identifier"
    )
    
    content = Text(
        null=True,
        help_text="Post text content"
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
    
    link = JSONB(
        null=True,
        help_text="Link structure (JSONB): {url: str, type: str, ...}"
    )
    
    message_timestamp = Timestamp(
        null=True,
        help_text="Post publication timestamp"
    )
    
    has_reactions = Boolean(
        null=True,
        default=False,
        help_text="Whether post has reactions"
    )
    
    id_channels = Integer(
        null=True,
        help_text="Foreign key to channel (external microservice)"
    )
    
    free_reactions_count = Integer(
        null=True,
        default=0,
        help_text="Count of free reactions"
    )
    
    paid_reactions_count = Integer(
        null=True,
        default=0,
        help_text="Count of paid reactions"
    )

