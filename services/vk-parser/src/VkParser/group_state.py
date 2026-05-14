from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.VkParser.vk_raw_types import VkWallPostRaw


class group_state(BaseModel):
    """
    Состояние группы внутри пайплайна парсера.
    Хранит исходные поля группы + вычисляемые поля (posts_count, posts).
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str | None = None
    screen_name: str | None = None
    members_count: int | None = None
    photo_url: str | None = None
    cover_url: str | None = None

    posts_count: int = 0
    posts: list[VkWallPostRaw] = Field(default_factory=list)
