from __future__ import annotations

from litestar import MediaType, get


@get("/health", media_type=MediaType.JSON)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "recs_api"}


@get("/recommend", media_type=MediaType.JSON)
async def recommend() -> dict[str, object]:
    # TODO: accept query params, call search + ranker, return results
    return {"recommendations": [], "message": "not implemented"}
