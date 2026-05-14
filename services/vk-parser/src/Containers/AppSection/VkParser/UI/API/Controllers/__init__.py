"""API Controllers."""

from src.Containers.AppSection.VkParser.UI.API.Controllers.VkParserController import (
    VkHealthController,
    VkParserController,
    VkSearchController,
)
from src.Containers.AppSection.VkParser.UI.API.Controllers.VkReadController import (
    VkGroupsController,
    VkPostsController,
)

__all__ = [
    "VkParserController",
    "VkSearchController",
    "VkHealthController",
    "VkGroupsController",
    "VkPostsController",
]
