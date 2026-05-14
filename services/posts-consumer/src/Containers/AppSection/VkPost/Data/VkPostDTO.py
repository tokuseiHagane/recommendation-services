from datetime import datetime

from pydantic import BaseModel, Field


class VkPostDTO(BaseModel):
    """Kafka DTO for VK posts, aligned with VKParserService broker payloads."""

    id: int = Field(..., description="Post ID")
    len_message: int | None = Field(None, description="Post text length")
    repost_count: int = Field(0, description="Repost count")
    view_count: int = Field(0, description="View count")
    comments_count: int = Field(0, description="Comments count")
    message_timestamp: datetime | None = Field(None, description="Post timestamp")
    edit_date: datetime | None = Field(None, description="Edit timestamp")
    reactions_count: int = Field(0, description="Total reactions count")
    id_groups: int | None = Field(None, description="VK group ID")
