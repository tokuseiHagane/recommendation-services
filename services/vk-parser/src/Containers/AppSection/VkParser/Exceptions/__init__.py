"""VkParser Exceptions."""

from src.Containers.AppSection.VkParser.Exceptions.VkParserException import (
    VkApiError,
    VkAuthenticationError,
    VkParserException,
    VkRateLimitError,
)

__all__ = [
    "VkParserException",
    "VkApiError",
    "VkAuthenticationError",
    "VkRateLimitError",
]
