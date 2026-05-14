"""FindGroupsTask — query cached VK groups from PostgreSQL."""

from dataclasses import dataclass
from typing import Any

from src.Containers.AppSection.VkParser.Models.VkGroup import VkGroup
from src.Ship.Parents.Task import Task


@dataclass(frozen=True)
class FindGroupsInput:
    # Exact match by screen_name (used by internal parsing flow to locate a
    # single group by its VK domain — e.g. ParseVkDataAction cache lookup).
    screen_name: str | None = None
    # Substring (ILIKE) match across ``name`` and ``screen_name`` for the
    # user-facing catalog search (§3.1 design handoff).
    q: str | None = None
    limit: int = 50
    offset: int = 0


class FindGroupsTask(Task[FindGroupsInput, list[dict[str, Any]]]):
    """Return groups from the local cache DB."""

    async def run(self, data: FindGroupsInput) -> list[dict[str, Any]]:
        query = VkGroup.select()

        if data.screen_name:
            query = query.where(VkGroup.screen_name == data.screen_name)

        if data.q:
            pattern = f"%{data.q.strip()}%"
            query = query.where(
                (VkGroup.screen_name.ilike(pattern)) | (VkGroup.name.ilike(pattern))
            )

        rows = await query.order_by(VkGroup.id).limit(data.limit).offset(data.offset)
        return [dict(r) for r in rows]
