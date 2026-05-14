"""
Piccolo ORM configuration for Social Channel Consumer.

This configuration supports multiple databases:
- Telegram database (DB / TG_DB_*): for TgChannel model
- VK database (VK_DB_*): for VkGroup model

Each container uses its own database connection.
"""
from piccolo.conf.apps import AppConfig, AppRegistry
from piccolo.engine.postgres import PostgresEngine

from src.Ship.config.settings import settings
from src.Ship.utils.db import get_tg_db_engine, get_vk_db_engine


# Default DB engine (Telegram) for backward compatibility
DB = get_tg_db_engine()

# App registry with all containers
# Note: Each container may use a different database!
# - tg_channel uses TG database (DB)
# - vk_group uses VK database (requires separate engine)
APP_REGISTRY = AppRegistry(
    apps=[
        "src.Containers.tg_channel.PiccoloApp",
        "src.Containers.vk_group.PiccoloApp",
    ]
)


