from pydantic import BaseModel, Field


class GroupDTO(BaseModel):
    """Kafka DTO for VK groups, aligned with VKParserService broker payloads."""

    id: int = Field(..., description="Group ID")
    name: str | None = Field(None, description="Group name")
    screen_name: str | None = Field(None, description="Group screen name")
    members_count: int | None = Field(None, description="Members count")
