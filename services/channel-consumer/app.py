"""
Social Channel Consumer - Distributed Monolith Application

This application processes social network data from Kafka:
- Telegram channels (TG module)
- VK groups (VK module)

Modules can be enabled/disabled via environment variables:
- ENABLE_TG_MODULE=true/false
- ENABLE_VK_MODULE=true/false

Each module uses a separate database:
- Telegram: DB_* or TG_DB_* env vars
- VK: VK_DB_* env vars
"""
import asyncio
import logging
from litestar import Litestar, get
from contextlib import asynccontextmanager
from typing import List

from src.Ship.config.logging import configure_logging
from src.Ship.config.settings import settings
from src.Ship.Providers import container as di_container


logger = logging.getLogger(__name__)


# Store background tasks for cleanup
_background_tasks: List[asyncio.Task] = []


def _health_payload() -> dict[str, object]:
    """Build a JSON-serialisable health payload."""
    return {
        "status": "ok",
        "modules": {
            "telegram": "enabled" if settings.ENABLE_TG_MODULE else "disabled",
            "vk": "enabled" if settings.ENABLE_VK_MODULE else "disabled",
        },
        "running_consumers": len(_background_tasks),
    }


async def start_tg_module() -> asyncio.Task | None:
    """
    Start Telegram module: create tables and start Kafka consumer.
    
    Returns:
        Background task for Kafka consumer, or None if module disabled
    """
    if not settings.ENABLE_TG_MODULE:
        logger.info("Telegram module is DISABLED")
        return None
    
    logger.info("Starting Telegram module...")
    
    # Import lazily to avoid circular imports and allow module toggling
    from src.Containers.tg_channel.model.tg_channel_model import create_tables as create_tg_tables
    from src.Ship.tasks.tg_channel_kafka_worker import consume_tg_channels
    from src.Ship.utils.kafka_admin import ensure_tg_topics
    
    # Create Kafka topics
    ensure_tg_topics()
    
    # Auto-create database tables
    await create_tg_tables()
    
    # Start Kafka consumer
    task = asyncio.create_task(
        consume_tg_channels(di=di_container, initialize_cache=True)
    )
    
    logger.info("Telegram module started: Kafka consumer running")
    return task


async def start_vk_module() -> asyncio.Task | None:
    """
    Start VK module: create tables and start Kafka consumer.
    
    Returns:
        Background task for Kafka consumer, or None if module disabled
    """
    if not settings.ENABLE_VK_MODULE:
        logger.info("VK module is DISABLED")
        return None
    
    logger.info("Starting VK module...")
    
    # Import lazily to avoid circular imports and allow module toggling
    from src.Containers.vk_group.model.vk_group_model import create_tables as create_vk_tables
    from src.Ship.tasks.vk_group_kafka_worker import consume_vk_groups
    from src.Ship.utils.kafka_admin import ensure_vk_topics
    
    # Create Kafka topics
    ensure_vk_topics()
    
    # Auto-create database tables
    await create_vk_tables()
    
    # Start Kafka consumer
    task = asyncio.create_task(
        consume_vk_groups(di=di_container, initialize_cache=True)
    )
    
    logger.info("VK module started: Kafka consumer running")
    return task


@asynccontextmanager
async def lifespan(app: Litestar):
    """
    Application lifecycle manager for distributed monolith.
    
    Startup:
    - Configure logging
    - Start enabled modules (TG and/or VK)
    - Each module creates its own Kafka topics and DB tables
    - Each module starts its own Kafka consumer
    
    Shutdown:
    - Cancel all Kafka consumer tasks
    - Graceful cleanup for each module
    """
    global _background_tasks
    
    configure_logging(settings.LOG_LEVEL)
    
    logger.info("=" * 60)
    logger.info("Social Channel Consumer - Starting")
    logger.info(f"  Telegram module: {'ENABLED' if settings.ENABLE_TG_MODULE else 'DISABLED'}")
    logger.info(f"  VK module: {'ENABLED' if settings.ENABLE_VK_MODULE else 'DISABLED'}")
    logger.info("=" * 60)
    
    # Start modules in parallel
    tg_task, vk_task = await asyncio.gather(
        start_tg_module(),
        start_vk_module(),
    )
    
    # Collect running tasks
    _background_tasks = [t for t in [tg_task, vk_task] if t is not None]
    
    if not _background_tasks:
        logger.warning("No modules enabled! Application will only serve health checks.")
    else:
        logger.info(f"Started {len(_background_tasks)} module(s)")
    
    try:
        yield
    finally:
        logger.info("Application shutting down...")
        
        # Cancel all consumer tasks
        for task in _background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        for task in _background_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.info("All modules stopped. Goodbye!")


@get("/")
async def health_check() -> dict[str, object]:
    """Health check endpoint with module status."""
    return _health_payload()


@get("/health")
async def health() -> dict[str, object]:
    """Alias for health check."""
    return _health_payload()


app = Litestar(route_handlers=[health_check, health], lifespan=[lifespan])
