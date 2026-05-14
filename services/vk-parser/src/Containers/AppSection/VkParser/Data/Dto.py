"""Data Transfer Objects for VK Parser."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SortParamConfig(BaseModel):
    """Configuration for a single sort parameter."""

    priority: int = Field(default=1, description="Sort priority (higher = more important)")
    reverse: bool = Field(default=False, description="Reverse sort order")


class SortParams(BaseModel):
    """Sort parameters for posts."""

    date: SortParamConfig = Field(default_factory=lambda: SortParamConfig(priority=1, reverse=False))
    engagement_rate: SortParamConfig = Field(default_factory=lambda: SortParamConfig(priority=1, reverse=True))
    views: SortParamConfig = Field(default_factory=lambda: SortParamConfig(priority=1, reverse=True))
    comments: SortParamConfig = Field(default_factory=lambda: SortParamConfig(priority=1, reverse=True))
    reposts: SortParamConfig = Field(default_factory=lambda: SortParamConfig(priority=1, reverse=True))


class VkParseRequest(BaseModel):
    """Request for VK parsing."""

    links: list[str] = Field(..., description="List of VK profile/group links")
    start_date: datetime = Field(..., description="Start date for posts")
    end_date: datetime = Field(..., description="End date for posts")
    top_n: int = Field(default=10, description="Number of top posts to return")
    parse_all: bool = Field(
        default=False,
        description="Force full re-parse even if cached (ignored when data < 24h old)",
    )
    sort_params: SortParams = Field(default_factory=SortParams, description="Sort parameters")

    @field_validator("start_date", "end_date", mode="after")
    @classmethod
    def _ensure_tz_aware_utc(cls, value: datetime) -> datetime:
        """Normalize naive datetimes to UTC-aware.

        Piccolo's ``Timestamptz`` columns (used by ``CachedPeriod``) always
        return tz-aware datetimes. If the client sends a date-only or naive
        ISO string, ``CacheCheckTask.calculate_missing_periods`` would raise
        ``TypeError: can't compare offset-naive and offset-aware datetimes``
        once the cache has at least one entry. Assuming UTC keeps the API
        backwards compatible while preventing the crash.
        """

        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "links": ["https://vk.com/lentach", "https://vk.com/mdk"],
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-31T23:59:59",
                "top_n": 10,
                "parse_all": False,
                "sort_params": {
                    "date": {"priority": 1, "reverse": False},
                    "views": {"priority": 2, "reverse": True},
                },
            }
        }
    }


class VkParseResponse(BaseModel):
    """Response from VK parsing."""

    data: dict[str, Any] = Field(..., description="Parsed VK data by domain")
    domains_count: int = Field(..., description="Number of processed domains")


class VkSearchRequest(BaseModel):
    """Request for VK search."""

    query: str = Field(..., min_length=1, description="Search query")

    model_config = {"json_schema_extra": {"example": {"query": "lentach"}}}


class VkSearchResponse(BaseModel):
    """Response from VK search."""

    items: list[dict[str, Any]] = Field(default_factory=list, description="Search results")


# ---------- Kafka broker DTOs (aligned with consumer contracts) ----------


class KafkaGroupMessage(BaseModel):
    """Message published to ``vk_groups`` topic.

    Schema aligned with Telegram-Channel-Consumer ``VkGroupSchema``.
    """

    id: int
    name: str | None = None
    screen_name: str | None = None
    members_count: int | None = None


class KafkaPostMessage(BaseModel):
    """Message published to ``vk_posts_{group_id}`` topic.

    Schema aligned with Telegram-Posts-Consumers ``VkPostDTO``.
    """

    id: int
    len_message: int | None = None
    repost_count: int = 0
    view_count: int = 0
    comments_count: int = 0
    message_timestamp: datetime | None = None
    edit_date: datetime | None = None
    reactions_count: int = 0
    id_groups: int | None = None
