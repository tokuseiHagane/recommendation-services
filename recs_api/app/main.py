from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from litestar import Litestar
from litestar.openapi import OpenAPIConfig

from recs_api.app.routes import health_check, recommend
from recs_api.app.search import SearchService
from shared.config import settings
from shared.db import DB
from shared.telemetry import configure_telemetry
from shared.models.recommendations import (
    RecommendationCandidate,
    RecommendationFeedback,
    RecommendationRequest,
    RecommendationResult,
)


@asynccontextmanager
async def search_service_lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    await DB.start_connection_pool()

    for table_cls in (
        RecommendationRequest,
        RecommendationCandidate,
        RecommendationResult,
        RecommendationFeedback,
    ):
        await table_cls.create_table(if_not_exists=True).run()

    svc = SearchService(settings.OPENSEARCH_URL)
    app.state.search_service = svc
    try:
        yield
    finally:
        await svc.close()
        await DB.close_connection_pool()


def create_app() -> Litestar:
    plugins = configure_telemetry()
    return Litestar(
        route_handlers=[health_check, recommend],
        lifespan=[search_service_lifespan],
        plugins=plugins,
        openapi_config=OpenAPIConfig(
            title="Recommendation API",
            version="0.1.0",
            description="REST API для подбора рекламных площадок по текстовому запросу",
        ),
        debug=True,
    )


app = create_app()
