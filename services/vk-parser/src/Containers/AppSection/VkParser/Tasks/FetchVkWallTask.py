"""FetchVkWallTask — fetch VK wall data via the internal runtime service."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.Ship.Parents.Task import Task


@dataclass(frozen=True)
class FetchVkWallInput:
    vk_token: str
    links: list[str]
    start_date: datetime
    end_date: datetime
    top_n: int
    sort_params: dict[str, Any]


class FetchVkWallTask(Task[FetchVkWallInput, dict[str, Any]]):
    """Fetch VK wall data as an atomic Porto Task."""

    async def run(self, data: FetchVkWallInput) -> dict[str, Any]:
        from src.VkParser.service import get_vk_data

        result = await get_vk_data(
            token=data.vk_token,
            links=data.links,
            start_date=data.start_date,
            end_date=data.end_date,
            top_n=data.top_n,
            sort_params=data.sort_params,
        )
        return result or {}
