from piccolo.engine.postgres import PostgresEngine
from src.Ship.config.settings import settings

# Telegram database engine (singleton)
_tg_engine: PostgresEngine | None = None

# VK database engine (singleton)
_vk_engine: PostgresEngine | None = None


def get_tg_db_engine() -> PostgresEngine:
    """Return the global Piccolo engine instance for Telegram database."""
    global _tg_engine
    if _tg_engine is None:
        _tg_engine = PostgresEngine(
            config={
                "database": settings.TG_DB_NAME,
                "user": settings.TG_DB_USER,
                "password": settings.TG_DB_PASSWORD,
                "host": settings.TG_DB_HOST,
                "port": settings.TG_DB_PORT,
            }
        )
    return _tg_engine


def get_vk_db_engine() -> PostgresEngine:
    """Return the global Piccolo engine instance for VK database."""
    global _vk_engine
    if _vk_engine is None:
        _vk_engine = PostgresEngine(
            config={
                "database": settings.VK_DB_NAME,
                "user": settings.VK_DB_USER,
                "password": settings.VK_DB_PASSWORD,
                "host": settings.VK_DB_HOST,
                "port": settings.VK_DB_PORT,
            }
        )
    return _vk_engine


# Backward compatibility alias
def get_db_engine() -> PostgresEngine:
    """Return the global Piccolo engine instance (Telegram DB for backward compatibility)."""
    return get_tg_db_engine()


def init_db() -> None:
    """Initialize Piccolo ORM engine globally.
    
    This is called when models are imported and ensures the engine is created.
    The actual engine configuration is in piccolo_conf.py.
    """
    # Just ensure the engine is created
    get_tg_db_engine()


def init_vk_db() -> None:
    """Initialize Piccolo ORM engine for VK database.
    
    This is called when VK models are imported and ensures the engine is created.
    """
    get_vk_db_engine()
