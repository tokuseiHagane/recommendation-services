"""ListGroupsAction — list cached VK groups."""

from typing import Any

from src.Containers.AppSection.VkParser.Tasks.FindGroupsTask import FindGroupsInput, FindGroupsTask
from src.Ship.Parents.Action import Action


class ListGroupsAction(Action[FindGroupsInput, list[dict[str, Any]]]):
    """Return groups from local DB cache."""

    def __init__(self, find_groups_task: FindGroupsTask) -> None:
        self._find_groups = find_groups_task

    async def run(self, data: FindGroupsInput) -> list[dict[str, Any]]:
        return await self._find_groups.execute(data)
