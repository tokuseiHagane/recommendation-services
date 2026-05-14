from piccolo.engine.postgres import PostgresEngine

from shared.config import settings

DB = PostgresEngine(
    config={
        "dsn": settings.DATABASE_URL,
    }
)
