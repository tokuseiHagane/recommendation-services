"""CheckGroupsExistAction — bulk "is this group in our cache?" lookup."""

from src.Containers.AppSection.VkParser.Tasks.GroupsExistTask import (
    GroupsExistInput,
    GroupsExistTask,
)
from src.Ship.Parents.Action import Action


class CheckGroupsExistAction(Action[list[int], dict[int, bool]]):
    """Used by both REST (`/groups/exists`) and WS enrich."""

    def __init__(self, groups_exist_task: GroupsExistTask) -> None:
        self._groups_exist = groups_exist_task

    async def run(self, data: list[int]) -> dict[int, bool]:
        return await self._groups_exist.execute(GroupsExistInput(ids=data))
