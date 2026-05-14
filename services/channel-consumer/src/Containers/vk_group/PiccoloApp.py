"""
Piccolo App configuration for VkGroup container.

This file is required for Piccolo migrations system.

IMPORTANT: VK groups use a SEPARATE database (vk) configured via VK_DB_* env vars.
"""
import os

from piccolo.conf.apps import AppRegistry
from piccolo.conf.apps import AppConfig


CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


APP_CONFIG = AppConfig(
    app_name="vk_group",
    migrations_folder_path=os.path.join(CURRENT_DIRECTORY, "migrations"),
    table_classes=[
        "src.Containers.vk_group.model.vk_group_model.VkGroup",
    ],
    migration_dependencies=[],
    commands=[],
)
