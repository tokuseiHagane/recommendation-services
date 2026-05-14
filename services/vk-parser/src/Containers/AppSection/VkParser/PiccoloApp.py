"""Piccolo App configuration for VkParser container."""

import os

from piccolo.conf.apps import AppConfig

from src.Containers.AppSection.VkParser.Models.AccountTokens import AccountTokens
from src.Containers.AppSection.VkParser.Models.CachedPeriod import CachedPeriod
from src.Containers.AppSection.VkParser.Models.VkGroup import VkGroup
from src.Containers.AppSection.VkParser.Models.VkPost import VkPost

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

APP_CONFIG = AppConfig(
    app_name="vk_parser",
    table_classes=[AccountTokens, VkGroup, VkPost, CachedPeriod],
    migrations_folder_path=os.path.join(CURRENT_DIRECTORY, "piccolo_migrations"),
    migration_dependencies=[],
    commands=[],
)
