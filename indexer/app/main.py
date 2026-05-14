from __future__ import annotations

from litestar import Litestar, MediaType, get


@get("/health", media_type=MediaType.JSON)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "indexer"}


def create_app() -> Litestar:
    return Litestar(
        route_handlers=[health_check],
        debug=True,
    )


app = create_app()
