from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from litestar import Litestar, MediaType, get
from litestar.datastructures import State

from shared.config import settings
from shared.db import DB
from shared.telemetry import configure_otel
from shared.models.recommendations import IndexSyncLog

from indexer.app.opensearch_client import RESOURCE_DOCUMENTS_MAPPING, OpenSearchClient
from indexer.app.service import INDEX_NAME, sync_cycle

logger = logging.getLogger(__name__)

_sync_stats: dict[str, Any] = {
    "last_sync": None,
    "docs_indexed": 0,
    "running": False,
}


async def _run_sync(os_client: OpenSearchClient) -> None:
    if _sync_stats["running"]:
        logger.warning("Sync already running, skipping")
        return
    _sync_stats["running"] = True
    try:
        result = await sync_cycle(os_client)
        _sync_stats["last_sync"] = datetime.now(timezone.utc).isoformat()
        _sync_stats["docs_indexed"] += result["synced"]
    except Exception:
        logger.exception("Sync cycle failed")
    finally:
        _sync_stats["running"] = False


@asynccontextmanager
async def indexer_lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    await DB.start_connection_pool()
    await IndexSyncLog.create_table(if_not_exists=True).run()

    os_client = OpenSearchClient(settings.OPENSEARCH_URL)
    await os_client.ensure_index(INDEX_NAME, RESOURCE_DOCUMENTS_MAPPING)
    app.state.os_client = os_client

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_sync,
        "interval",
        seconds=settings.POLLING_INTERVAL_SECONDS,
        args=[os_client],
        id="sync_cycle",
        replace_existing=True,
    )
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info(
        "Indexer started, polling every %ds", settings.POLLING_INTERVAL_SECONDS
    )

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await os_client.close()
        await DB.close_connection_pool()
        logger.info("Indexer shut down")


@get("/health", media_type=MediaType.JSON)
async def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "indexer",
        "last_sync": _sync_stats["last_sync"],
        "docs_indexed": _sync_stats["docs_indexed"],
    }


@get("/trigger", media_type=MediaType.JSON)
async def trigger_sync(state: State) -> dict[str, Any]:
    os_client: OpenSearchClient = state.os_client
    if _sync_stats["running"]:
        return {"status": "already_running"}

    asyncio.create_task(_run_sync(os_client))
    return {"status": "triggered"}


def create_app() -> Litestar:
    otel_cfg = configure_otel()
    mw = [otel_cfg.middleware] if otel_cfg else []
    return Litestar(
        route_handlers=[health_check, trigger_sync],
        lifespan=[indexer_lifespan],
        middleware=mw,
        debug=True,
    )


app = create_app()
