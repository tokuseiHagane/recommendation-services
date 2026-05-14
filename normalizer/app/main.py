from __future__ import annotations

from litestar import Litestar, MediaType, get


@get("/health", media_type=MediaType.JSON)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "normalizer"}


def create_app() -> Litestar:
    # TODO: wire APScheduler for periodic normalize jobs
    return Litestar(
        route_handlers=[health_check],
        debug=True,
    )


app = create_app()
