"""
Piccolo configuration for VK database.

This is a separate configuration for VkPost container,
connecting to the VK database instead of the default post_db.

Usage:
    PICCOLO_CONF=piccolo_conf_vk piccolo migrations forwards VkPost
"""
from piccolo.conf.apps import AppRegistry

from src.Ship.utils.db import get_db_engine


# VK database engine
DB = get_db_engine(db_name="vk")

# Registry для VkPost Piccolo app
APP_REGISTRY = AppRegistry(
    apps=[
        "src.Containers.AppSection.VkPost.PiccoloApp",
    ]
)
