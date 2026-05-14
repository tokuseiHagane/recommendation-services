from piccolo.engine.postgres import PostgresEngine
from src.Ship.config.settings import settings

# Multi-database support: named engines
_engines: dict[str, PostgresEngine] = {}


def get_db_engine(db_name: str = "default") -> PostgresEngine:
    """
    Return the Piccolo engine instance for the specified database.
    
    Supports multiple databases for distributed monolith architecture:
    - "default" - TgPost database (post_db)
    - "vk" - VkPost database (vk)
    
    Args:
        db_name: Database identifier ("default" for TgPost, "vk" for VkPost)
        
    Returns:
        PostgresEngine configured for the specified database.
    """
    global _engines
    if db_name not in _engines:
        config = settings.get_db_config(db_name)
        _engines[db_name] = PostgresEngine(config=config)
    return _engines[db_name]


def init_db(db_name: str = "default") -> None:
    """
    Initialize Piccolo ORM engine globally.
    
    This is called when models are imported and ensures the engine is created.
    The actual engine configuration is in piccolo_conf.py or piccolo_conf_vk.py.
    
    Args:
        db_name: Database identifier to initialize
    """
    # Just ensure the engine is created
    get_db_engine(db_name)


def init_all_dbs() -> None:
    """Initialize all database engines."""
    init_db("default")
    init_db("vk")
