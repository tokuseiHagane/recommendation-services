"""FindGroupByIdTask — fetch a single cached VK group with cached posts count."""

from dataclasses import dataclass
from typing import Any

from src.Containers.AppSection.VkParser.Models.VkGroup import VkGroup
from src.Containers.AppSection.VkParser.Models.VkPost import VkPost
from src.Ship.Parents.Task import Task


@dataclass(frozen=True)
class FindGroupByIdInput:
    group_id: int


class FindGroupByIdTask(Task[FindGroupByIdInput, dict[str, Any] | None]):
    """Return one group row from cache enriched with a local posts count."""

    async def run(self, data: FindGroupByIdInput) -> dict[str, Any] | None:
        rows = await VkGroup.select().where(VkGroup.id == data.group_id).limit(1)
        if not rows:
            return None

        group = dict(rows[0])
        posts_count_rows = await VkPost.count().where(VkPost.id_groups == data.group_id)
        group["posts_count"] = int(posts_count_rows or 0)
        return group
