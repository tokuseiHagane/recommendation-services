"""SearchVkAction — orchestrate VK search through Tasks."""

from typing import Any

import logfire

from src.Containers.AppSection.VkParser.Tasks.SearchVkTask import SearchVkInput, SearchVkTask
from src.Ship.Parents.Action import Action


class SearchVkAction(Action[tuple[str, str], dict[str, Any]]):
    """Orchestrate VK search via Porto Tasks."""

    def __init__(self, search_vk_task: SearchVkTask) -> None:
        self._search_vk = search_vk_task

    async def run(self, data: tuple[str, str]) -> dict[str, Any]:
        vk_token, query = data

        logfire.info("VK search", query=query)

        result = await self._search_vk.execute(SearchVkInput(vk_token=vk_token, query=query))

        logfire.info("VK search completed", results_count=len(result.get("items", [])))
        return result
