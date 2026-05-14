"""GroupsExistTask — bulk-check which VK group ids are present in our cache."""

from dataclasses import dataclass

from src.Containers.AppSection.VkParser.Models.VkGroup import VkGroup
from src.Ship.Parents.Task import Task


@dataclass(frozen=True)
class GroupsExistInput:
    ids: list[int]


class GroupsExistTask(Task[GroupsExistInput, dict[int, bool]]):
    """Return ``{group_id: True|False}`` for every requested id.

    Used by the search UI to render the "already in DB / new" marker next to
    each VK search hint (§3.4 in the design handoff) without issuing one
    round-trip per item.
    """

    async def run(self, data: GroupsExistInput) -> dict[int, bool]:
        if not data.ids:
            return {}

        unique_ids = list({int(gid) for gid in data.ids if gid is not None})
        if not unique_ids:
            return {}

        rows = await VkGroup.select(VkGroup.id).where(VkGroup.id.is_in(unique_ids))
        present = {int(row["id"]) for row in rows}
        return {gid: (gid in present) for gid in unique_ids}
