"""Add ``photo_url`` and ``cover_url`` to the cached ``groups`` table.

Drives §3.2 (group detail) and §3.4 (search hints with a group avatar) in
the design handoff. Both columns are nullable so existing rows stay valid.
"""

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns import Text

ID = "2026-04-23T12:00:00"
VERSION = "1.30.0"
DESCRIPTION = "Add photo_url and cover_url to VkGroup"


async def forwards() -> MigrationManager:
    manager = MigrationManager(
        migration_id=ID,
        app_name="vk_parser",
        description=DESCRIPTION,
    )

    manager.add_column(
        table_class_name="VkGroup",
        tablename="groups",
        column_name="photo_url",
        db_column_name="photo_url",
        column_class_name="Text",
        column_class=Text,
        params={
            "null": True,
            "default": "",
            "primary_key": False,
            "unique": False,
            "index": False,
        },
    )

    manager.add_column(
        table_class_name="VkGroup",
        tablename="groups",
        column_name="cover_url",
        db_column_name="cover_url",
        column_class_name="Text",
        column_class=Text,
        params={
            "null": True,
            "default": "",
            "primary_key": False,
            "unique": False,
            "index": False,
        },
    )

    return manager
