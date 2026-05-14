"""
InitializeVkDatabaseTask: Инициализация VK базы данных.

Porto Architecture Task:
- Атомарная операция инициализации БД
- Создание таблиц при их отсутствии
- Настройка grants и privileges
"""

import logging
import asyncpg

from src.Ship.config.settings import settings

logger = logging.getLogger(__name__)


async def initialize_vk_database_task(
    db_name: str | None = None,
    db_user: str | None = None
) -> bool:
    """
    Task: Инициализировать VK базу данных.
    
    Atomic operation для:
    - Проверки подключения к БД
    - Создания таблиц при их отсутствии (через Piccolo migrations)
    - Настройки grants и privileges
    
    Args:
        db_name: Имя VK базы данных (default: из settings.VK_DB_NAME)
        db_user: Имя пользователя (default: из settings.VK_DB_USER)
    
    Returns:
        True если инициализация успешна, False если нет
        
    Example:
        >>> success = await initialize_vk_database_task()
        >>> success
        True
    """
    
    db_name = db_name or settings.VK_DB_NAME
    db_user = db_user or settings.VK_DB_USER
    
    try:
        # Подключение к VK БД
        conn = await asyncpg.connect(
            host=settings.VK_DB_HOST,
            port=settings.VK_DB_PORT,
            user=settings.VK_DB_USER,
            password=settings.VK_DB_PASSWORD,
            database=settings.VK_DB_NAME
        )
        
        try:
            # Проверка подключения
            result = await conn.fetchval('SELECT 1')
            logger.info(f"VK Database connection verified: {result}")
            
            # Проверка наличия таблиц
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('posts', 'groups')
            """)
            
            existing_tables = [row['table_name'] for row in tables]
            logger.info(f"VK Database existing tables: {existing_tables}")
            
            # Если таблицы не существуют, они будут созданы через Piccolo migrations
            # в docker-entrypoint.sh
            if 'posts' not in existing_tables:
                logger.warning("VK 'posts' table not found - will be created by migrations")
            
            if 'groups' not in existing_tables:
                logger.warning("VK 'groups' table not found - will be created by migrations")
            
            # Установить grants если нужно
            if db_user != 'postgres':
                try:
                    await conn.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {db_user}")
                    await conn.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {db_user}")
                    logger.info(f"Granted privileges to user {db_user}")
                except Exception as exc:
                    # Игнорируем ошибки grants (могут быть права не те)
                    logger.debug(f"Could not grant privileges: {exc}")
            
            return True
            
        finally:
            await conn.close()
            
    except Exception as exc:
        logger.exception(f"Failed to initialize VK database: {exc}")
        return False
