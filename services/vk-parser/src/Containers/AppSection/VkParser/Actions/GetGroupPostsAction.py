"""GetGroupPostsAction — get cached posts for a VK group."""

from typing import Any

from src.Containers.AppSection.VkParser.Tasks.FindPostsTask import FindPostsInput, FindPostsTask
from src.Ship.Parents.Action import Action


class GetGroupPostsAction(Action[FindPostsInput, list[dict[str, Any]]]):
    """Return posts for a group from local DB cache."""

    def __init__(self, find_posts_task: FindPostsTask) -> None:
        self._find_posts = find_posts_task

    async def run(self, data: FindPostsInput) -> list[dict[str, Any]]:
        return await self._find_posts.execute(data)
