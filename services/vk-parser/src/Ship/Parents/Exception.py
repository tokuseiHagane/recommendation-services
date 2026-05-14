"""Base Exception class according to Porto architecture."""


class PortoException(Exception):
    """Base exception class for Porto architecture.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        status_code: int = 500,
        details: dict | None = None,
    ) -> None:
        """Initialize exception.

        Args:
            message: Error message
            code: Error code for identification
            status_code: HTTP status code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> dict:
        """Convert exception to dictionary."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }
