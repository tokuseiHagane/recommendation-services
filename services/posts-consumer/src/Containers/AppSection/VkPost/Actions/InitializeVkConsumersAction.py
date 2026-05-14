"""
InitializeVkConsumersAction: Инициализация VK консьюмеров при старте.

Porto Architecture Action:
- Оркестрирует LoadGroupsFromDBTask → UpdateCacheTask → CreateKafkaConsumerTask + RegisterConsumerTask
- Logfire трассировка для observability
- Error handling с graceful degradation
"""

from typing import List, Any
import logging

try:
    import logfire
except ImportError:
    # Fallback если logfire не установлен
    class logfire:  # type: ignore
        @staticmethod
        def span(*args, **kwargs):
            from contextlib import contextmanager
            @contextmanager
            def dummy_span():
                yield
            return dummy_span()
        
        @staticmethod
        def info(*args, **kwargs):
            pass
        
        @staticmethod
        def warning(*args, **kwargs):
            pass

from src.Containers.AppSection.VkPost.Tasks.LoadGroupsFromDBTask import load_groups_from_db_task
from src.Containers.AppSection.VkPost.Tasks.UpdateCacheTask import update_cache_task
from src.Containers.AppSection.VkPost.Tasks.CreateKafkaConsumerTask import create_kafka_consumer_task
from src.Containers.AppSection.VkPost.Tasks.RegisterConsumerTask import register_consumer_task

logger = logging.getLogger(__name__)


async def initialize_vk_consumers_action(
    *,
    cache: Any,  # VkGroupsCache
    manager: Any,  # VkDynamicConsumerManager
    bootstrap_servers: str,
    topic_prefix: str = "vk_posts_"
) -> int:
    """
    Action: Инициализировать VK консьюмеры из БД при старте.
    
    Бизнес use case для инициализации всех консьюмеров для существующих VK групп.
    Оркестрирует:
    1. LoadGroupsFromDBTask - загрузка VK групп из БД
    2. UpdateCacheTask - синхронизация кэша
    3. Для каждой группы:
       a. CreateKafkaConsumerTask - создание консьюмера
       b. RegisterConsumerTask - регистрация в менеджере
    
    Args:
        cache: VkGroupsCache instance (DI)
        manager: VkDynamicConsumerManager instance (DI)
        bootstrap_servers: Kafka bootstrap servers
        topic_prefix: Префикс для VK топиков (default: vk_posts_)
    
    Returns:
        Количество созданных консьюмеров
        
    Example:
        >>> count = await initialize_vk_consumers_action(
        ...     cache=cache,
        ...     manager=manager,
        ...     bootstrap_servers="localhost:9092"
        ... )
        >>> count
        5
    """
    
    with logfire.span("initialize_vk_consumers_action"):
        try:
            # 1. Загрузка VK групп из БД
            with logfire.span("load_groups_from_db"):
                groups = await load_groups_from_db_task()
                
                logger.info(f"Loaded {len(groups)} VK groups from DB")
                logfire.info(
                    "VK Groups loaded from DB",
                    total_groups=len(groups)
                )
            
            if not groups:
                logger.warning("No VK groups found in DB, skipping initialization")
                return 0
            
            # 2. Синхронизация кэша
            with logfire.span("sync_cache"):
                await update_cache_task(cache, groups)
                logger.info(f"Synchronized cache with {len(groups)} VK groups")
            
            # 3. Создание консьюмеров для каждой группы
            created_count = 0
            failed_groups: List[int] = []
            
            for group in groups:
                group_id = group["id"]
                
                try:
                    with logfire.span(
                        "create_consumer_for_group",
                        group_id=group_id
                    ):
                        # 3a. Создать консьюмер
                        consumer = await create_kafka_consumer_task(
                            group_id=group_id,
                            bootstrap_servers=bootstrap_servers,
                            topic_prefix=topic_prefix
                        )
                        
                        # 3b. Зарегистрировать в менеджере
                        success = await register_consumer_task(
                            manager=manager,
                            group_id=group_id,
                            consumer=consumer
                        )
                        
                        if success:
                            created_count += 1
                            logger.debug(
                                f"Created VK consumer for group {group_id}"
                            )
                        else:
                            logger.warning(
                                f"Failed to register VK consumer for group {group_id}"
                            )
                            await consumer.stop()
                            failed_groups.append(group_id)
                
                except Exception as exc:
                    logger.error(
                        f"Failed to create VK consumer for group {group_id}: {exc}"
                    )
                    failed_groups.append(group_id)
                    continue
            
            logger.info(
                f"Initialized {created_count}/{len(groups)} VK consumers "
                f"(failed: {len(failed_groups)})"
            )
            
            logfire.info(
                "VK Consumers initialized",
                created=created_count,
                total_groups=len(groups),
                failed=len(failed_groups)
            )
            
            if failed_groups:
                logfire.warning(
                    "Some VK consumers failed to initialize",
                    failed_group_ids=failed_groups
                )
            
            return created_count
            
        except Exception as exc:
            logger.exception(
                f"Unexpected error in initialize_vk_consumers_action: {exc}"
            )
            return 0
