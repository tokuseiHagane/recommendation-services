"""
Piccolo ORM configuration for VK database.

This is a separate configuration file for VK models.
Use this when running migrations for VK database:

    PICCOLO_CONF=piccolo_conf_vk piccolo migrations forward vk_group
"""
from piccolo.conf.apps import AppConfig, AppRegistry
from piccolo.engine.postgres import PostgresEngine

from src.Ship.config.settings import settings
from src.Ship.utils.db import get_vk_db_engine


# VK database engine
DB = get_vk_db_engine()

# App registry for VK containers only
APP_REGISTRY = AppRegistry(
    apps=[
        "src.Containers.vk_group.PiccoloApp",
    ]
)
