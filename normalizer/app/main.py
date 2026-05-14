from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from litestar import Litestar, MediaType, get

from shared.config import settings
from shared.db import DB
from shared.telemetry import configure_telemetry
from shared.models.normalized import (
    AdResource,
    ResourceDocument,
    ResourceMetricSnapshot,
    ResourceTopicProfile,
    SourcePlatform,
)

from .service import normalize_cycle

logger = logging.getLogger(__name__)

_last_run: datetime | None = None


async def _scheduled_normalize() -> None:
    """Wrapper that tracks last run timestamp."""
    global _last_run  # noqa: PLW0603
    try:
        count = await normalize_cycle()
        _last_run = datetime.now(UTC)
        logger.info("Scheduled normalization done, processed %d groups", count)
    except Exception:
        logger.exception("Normalization cycle failed")


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    await DB.start_connection_pool()
    logger.info("DB connection pool started")

    for table_cls in (
        SourcePlatform,
        AdResource,
        ResourceTopicProfile,
        ResourceMetricSnapshot,
        ResourceDocument,
    ):
        await table_cls.create_table(if_not_exists=True).run()
    logger.info("Normalized tables ensured")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _scheduled_normalize,
        IntervalTrigger(seconds=settings.POLLING_INTERVAL_SECONDS),
        id="normalize",
        replace_existing=True,
    )
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Scheduler started (interval=%ds)", settings.POLLING_INTERVAL_SECONDS)

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await DB.close_connection_pool()
        logger.info("Shutdown complete")


@get("/health", media_type=MediaType.JSON)
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "normalizer",
        "last_run": _last_run.isoformat() if _last_run else None,
    }


@get("/trigger", media_type=MediaType.JSON)
async def trigger_normalize() -> dict:
    global _last_run  # noqa: PLW0603
    count = await normalize_cycle()
    _last_run = datetime.now(UTC)
    return {"status": "ok", "processed": count}


def create_app() -> Litestar:
    plugins = configure_telemetry()
    return Litestar(
        route_handlers=[health_check, trigger_normalize],
        lifespan=[lifespan],
        plugins=plugins,
        debug=True,
    )


app = create_app()
