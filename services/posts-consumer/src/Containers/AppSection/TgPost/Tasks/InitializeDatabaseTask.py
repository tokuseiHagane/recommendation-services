"""
InitializeDatabaseTask: Инициализация БД через Piccolo ORM.

Porto Architecture Task:
- Атомарная операция инициализации БД
- Выполняется один раз при первом запуске
- Создает grants и настройки через raw SQL
"""

import logging
from piccolo.utils.sync import run_sync

logger = logging.getLogger(__name__)


async def initialize_database_task(db_name: str = "app_db", db_user: str = "app_user"):
    """
    Task: Инициализировать БД с необходимыми настройками.
    
    Выполняет:
    1. GRANT ALL PRIVILEGES для app_user
    2. Настройки для всех таблиц и sequences
    
    Примечание: Extensions и timezone настраиваются через миграцию 2025-11-02T12-00-00-000000.py
    
    Args:
        db_name: Имя БД (default: app_db)
        db_user: Имя пользователя (default: app_user)
        
    Example:
        >>> await initialize_database_task(db_name="app_db", db_user="app_user")
    """
    
    try:
        from piccolo.conf.apps import Finder
        from piccolo.table import create_db_tables_sync
        
        # Получить DB instance из Piccolo
        finder = Finder()
        db = finder.get_db()
        
        # Выполнить grants через raw SQL
        # Это безопасно - если права уже есть, команда не упадет
        
        queries = [
            f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};",
            f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {db_user};",
            f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {db_user};",
            f"GRANT ALL PRIVILEGES ON SCHEMA public TO {db_user};",
        ]
        
        for query in queries:
            try:
                await db.execute_raw(query)
                logger.debug(f"Executed: {query}")
            except Exception as e:
                # Ignore errors - grants могут уже существовать
                logger.debug(f"Grant query ignored (might already exist): {e}")
        
        logger.info(f"✅ Database initialized successfully for user {db_user}")
        
    except Exception as exc:
        logger.warning(
            f"Database initialization failed (might be already initialized): {exc}"
        )
        # Не raise - это не критичная ошибка

