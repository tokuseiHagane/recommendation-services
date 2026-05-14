from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

from src.Ship.config.settings import settings
from src.Ship.utils.db import get_db_engine


DB = get_db_engine()

# Registry для всех Piccolo apps
APP_REGISTRY = AppRegistry(
    apps=[
        "src.Containers.AppSection.TgPost.PiccoloApp",
        # Legacy app (будет удален после миграции)
        # "src.Containers.message.migrations",
    ]
)


