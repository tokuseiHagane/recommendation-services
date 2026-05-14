"""
Social Channel Consumer - Bootstrap (Development Mode)

This is a lightweight version of the application WITHOUT Kafka consumers.
Use this for local development and testing.

For full application with Kafka consumers, use app.py instead.

Modules can be enabled/disabled via environment variables:
- ENABLE_TG_MODULE=true/false
- ENABLE_VK_MODULE=true/false
"""
import logging
from contextlib import asynccontextmanager
from litestar import Litestar, get

from src.Ship.config.logging import configure_logging
from src.Ship.config.settings import settings


logger = logging.getLogger(__name__)


def _health_payload() -> dict[str, object]:
    """Build a JSON-serialisable health payload."""
    return {
        "status": "ok",
        "mode": "development",
        "modules": {
            "telegram": "enabled" if settings.ENABLE_TG_MODULE else "disabled",
            "vk": "enabled" if settings.ENABLE_VK_MODULE else "disabled",
        },
        "note": "Kafka consumers not running in dev mode",
    }


async def init_tg_module() -> None:
    """Initialize Telegram module: create tables (no Kafka consumer)."""
    if not settings.ENABLE_TG_MODULE:
        logger.info("Telegram module is DISABLED")
        return
    
    logger.info("Initializing Telegram module...")
    
    from src.Containers.tg_channel.model.tg_channel_model import create_tables as create_tg_tables
    from src.Ship.utils.kafka_admin import ensure_tg_topics
    
    # Create Kafka topics
    ensure_tg_topics()
    
    # Auto-create database tables
    await create_tg_tables()
    
    logger.info("Telegram module initialized (no consumer in dev mode)")


async def init_vk_module() -> None:
    """Initialize VK module: create tables (no Kafka consumer)."""
    if not settings.ENABLE_VK_MODULE:
        logger.info("VK module is DISABLED")
        return
    
    logger.info("Initializing VK module...")
    
    from src.Containers.vk_group.model.vk_group_model import create_tables as create_vk_tables
    from src.Ship.utils.kafka_admin import ensure_vk_topics
    
    # Create Kafka topics
    ensure_vk_topics()
    
    # Auto-create database tables
    await create_vk_tables()
    
    logger.info("VK module initialized (no consumer in dev mode)")


@asynccontextmanager
async def lifespan(app: Litestar):
    """
    Application lifecycle manager (Development Mode - no Kafka consumers).
    
    Startup:
    - Configure logging
    - Initialize enabled modules (create topics and tables)
    
    Shutdown:
    - Graceful cleanup
    
    Note: This does NOT start Kafka consumers. Use app.py for production.
    """
    configure_logging(settings.LOG_LEVEL)
    
    logger.info("=" * 60)
    logger.info("Social Channel Consumer - Bootstrap (DEV MODE)")
    logger.info(f"  Telegram module: {'ENABLED' if settings.ENABLE_TG_MODULE else 'DISABLED'}")
    logger.info(f"  VK module: {'ENABLED' if settings.ENABLE_VK_MODULE else 'DISABLED'}")
    logger.info("  NOTE: Kafka consumers are NOT started in dev mode")
    logger.info("=" * 60)
    
    # Initialize modules
    await init_tg_module()
    await init_vk_module()
    
    logger.info("Application started successfully (dev mode - no consumers).")
    try:
        yield
    finally:
        logger.info("Application shutting down.")


@get("/")
async def health_check() -> dict[str, object]:
    """Health check endpoint with module status."""
    return _health_payload()


@get("/health")
async def health() -> dict[str, object]:
    """Alias for health check."""
    return _health_payload()


app = Litestar(route_handlers=[health_check, health], lifespan=[lifespan])

if __name__ == "__main__":
    # For quick local run: uvicorn src.Bootstrap:app --reload
    import uvicorn

    uvicorn.run("src.Bootstrap:app", host="0.0.0.0", port=8000, reload=True)


