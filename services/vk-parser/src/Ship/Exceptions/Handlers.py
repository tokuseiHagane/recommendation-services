"""Exception handlers."""

import logfire
from litestar import Request, Response

from src.Ship.Parents.Exception import PortoException


def exception_handler(request: Request, exc: PortoException) -> Response:
    """Handle Porto exceptions.

    Args:
        request: HTTP request
        exc: Porto exception

    Returns:
        HTTP response
    """
    logfire.error(
        f"🚨 Porto exception: {type(exc).__name__}",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        exception_code=exc.code,
        request_path=request.url.path,
        request_method=request.method,
        status_code=exc.status_code,
        exc_info=True,
    )

    return Response(
        content=exc.to_dict(),
        status_code=exc.status_code,
    )
