"""GetGroupByIdAction — return a single cached VK group detail."""

from typing import Any

from src.Containers.AppSection.VkParser.Tasks.FindGroupByIdTask import (
    FindGroupByIdInput,
    FindGroupByIdTask,
)
from src.Ship.Parents.Action import Action


class GetGroupByIdAction(Action[int, dict[str, Any] | None]):
    """Detail card source for §3.2 (guest can open any cached group)."""

    def __init__(self, find_group_by_id_task: FindGroupByIdTask) -> None:
        self._find_group_by_id = find_group_by_id_task

    async def run(self, data: int) -> dict[str, Any] | None:
        return await self._find_group_by_id.execute(FindGroupByIdInput(group_id=data))
