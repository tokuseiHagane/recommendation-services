from pydantic import BaseModel, Field


class ChannelDTO(BaseModel):
    """DTO for Telegram channel metadata consumed from Kafka."""

    id: int = Field(..., description="Channel ID")
    name: str = Field(..., description="Channel name")
    type: str = Field(..., description="Channel type")
