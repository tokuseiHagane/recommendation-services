"""VK Parser specific exceptions."""

from src.Ship.Parents.Exception import PortoException


class VkParserException(PortoException):
    """Base exception for VK Parser operations."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        status_code: int = 500,
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code or "VK_PARSER_ERROR",
            status_code=status_code,
            details=details,
        )


class VkApiError(VkParserException):
    """VK API returned an error."""

    def __init__(
        self,
        message: str,
        vk_error_code: int | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VK_API_ERROR",
            status_code=502,
            details={
                "vk_error_code": vk_error_code,
                **(details or {}),
            },
        )


class VkAuthenticationError(VkParserException):
    """VK authentication failed."""

    def __init__(
        self,
        message: str = "VK authentication failed. Please check your token.",
        status_code: int = 401,
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VK_AUTH_ERROR",
            status_code=status_code,
            details=details,
        )


class VkRateLimitError(VkParserException):
    """VK API rate limit exceeded."""

    def __init__(
        self,
        message: str = "VK API rate limit exceeded. Please try again later.",
        retry_after: int | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VK_RATE_LIMIT",
            status_code=429,
            details={
                "retry_after": retry_after,
                **(details or {}),
            },
        )
