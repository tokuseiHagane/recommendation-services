from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text

ID = "2026-04-23T12:00:00:000000"
VERSION = "1.22.0"
DESCRIPTION = "Add photo_url and cover_url to groups"


async def forwards() -> MigrationManager:
    manager = MigrationManager(
        migration_id=ID,
        app_name="vk_group",
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
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": "btree",
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="VkGroup",
        tablename="groups",
        column_name="cover_url",
        db_column_name="cover_url",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": "btree",
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    return manager
