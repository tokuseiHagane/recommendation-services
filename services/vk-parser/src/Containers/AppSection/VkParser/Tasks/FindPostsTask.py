"""FindPostsTask — query cached VK posts from PostgreSQL."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.Containers.AppSection.VkParser.Models.VkPost import VkPost
from src.Ship.Parents.Task import Task


@dataclass(frozen=True)
class FindPostsInput:
    group_id: int
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int | None = 50
    offset: int = 0


class FindPostsTask(Task[FindPostsInput, list[dict[str, Any]]]):
    """Return posts for a group from the local cache DB."""

    async def run(self, data: FindPostsInput) -> list[dict[str, Any]]:
        query = VkPost.select().where(VkPost.id_groups == data.group_id)

        if data.start_date:
            query = query.where(VkPost.message_timestamp >= data.start_date)
        if data.end_date:
            query = query.where(VkPost.message_timestamp <= data.end_date)

        query = query.order_by(VkPost.message_timestamp, ascending=False)
        if data.limit is not None:
            query = query.limit(data.limit).offset(data.offset)

        rows = await query
        return [dict(r) for r in rows]
