"""
Piccolo App configuration for TgChannel container.

This file is required for Piccolo migrations system.
"""
import os

from piccolo.conf.apps import AppRegistry
from piccolo.conf.apps import AppConfig


CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


APP_CONFIG = AppConfig(
    app_name="tg_channel",
    migrations_folder_path=os.path.join(CURRENT_DIRECTORY, "migrations"),
    table_classes=[
        "src.Containers.tg_channel.model.tg_channel_model.TgChannel",
    ],
    migration_dependencies=[],
    commands=[],
)

