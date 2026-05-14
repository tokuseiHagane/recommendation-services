from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PostDTO(BaseModel):
    """DTO for Telegram posts consumed from Kafka."""

    id: int = Field(..., description="Post ID")
    content: str | None = Field(None, description="Post content")
    repost_count: int | None = Field(0, description="Repost count")
    view_count: int | None = Field(0, description="View count")
    link: dict[str, Any] | None = Field(None, description="Link JSON payload")
    message_timestamp: datetime | None = Field(None, description="Post timestamp")
    has_reactions: bool | None = Field(False, description="Has reactions flag")
    id_channels: int | None = Field(None, description="Channel ID")
    free_reactions_count: int | None = Field(0, description="Free reactions count")
    paid_reactions_count: int | None = Field(0, description="Paid reactions count")

    @field_validator("link")
    @classmethod
    def validate_link(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return value

        if "url" in value:
            return value

        if "links" in value and isinstance(value["links"], list):
            return value

        raise ValueError("Invalid link structure")
