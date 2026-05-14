"""
InitializeConsumersAction: Инициализация консьюмеров при старте.

Porto Architecture Action:
- Оркестрирует LoadChannelsFromDBTask → UpdateCacheTask → CreateKafkaConsumerTask + RegisterConsumerTask (для каждого канала)
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

from src.Containers.AppSection.TgPost.Tasks.LoadChannelsFromDBTask import load_channels_from_db_task
from src.Containers.AppSection.TgPost.Tasks.UpdateCacheTask import update_cache_task
from src.Containers.AppSection.TgPost.Tasks.CreateKafkaConsumerTask import create_kafka_consumer_task
from src.Containers.AppSection.TgPost.Tasks.RegisterConsumerTask import register_consumer_task

logger = logging.getLogger(__name__)


async def initialize_consumers_action(
    *,
    cache: Any,  # PostObjectsCache
    manager: Any,  # DynamicConsumerManager
    bootstrap_servers: str
) -> int:
    """
    Action: Инициализировать консьюмеры из БД при старте.
    
    Бизнес use case для инициализации всех консьюмеров для существующих каналов.
    Оркестрирует:
    1. LoadChannelsFromDBTask - загрузка каналов из БД
    2. UpdateCacheTask - синхронизация кэша
    3. Для каждого канала:
       a. CreateKafkaConsumerTask - создание консьюмера
       b. RegisterConsumerTask - регистрация в менеджере
    
    Args:
        cache: PostObjectsCache instance (DI)
        manager: DynamicConsumerManager instance (DI)
        bootstrap_servers: Kafka bootstrap servers
    
    Returns:
        Количество созданных консьюмеров
        
    Example:
        >>> count = await initialize_consumers_action(
        ...     cache=cache,
        ...     manager=manager,
        ...     bootstrap_servers="localhost:9092"
        ... )
        >>> count
        5
    """
    
    with logfire.span("initialize_consumers_action"):
        try:
            # 1. Загрузка каналов из БД
            with logfire.span("load_channels_from_db"):
                channels = await load_channels_from_db_task()
                
                logger.info(f"Loaded {len(channels)} channels from DB")
                logfire.info(
                    "Channels loaded from DB",
                    total_channels=len(channels)
                )
            
            if not channels:
                logger.warning("No channels found in DB, skipping initialization")
                return 0
            
            # 2. Синхронизация кэша
            with logfire.span("sync_cache"):
                await update_cache_task(cache, channels)
                logger.info(f"Synchronized cache with {len(channels)} channels")
            
            # 3. Создание консьюмеров для каждого канала
            created_count = 0
            failed_channels: List[int] = []
            
            for channel in channels:
                channel_id = channel["id"]
                
                try:
                    with logfire.span(
                        "create_consumer_for_channel",
                        channel_id=channel_id
                    ):
                        # 3a. Создать консьюмер
                        consumer = await create_kafka_consumer_task(
                            channel_id=channel_id,
                            bootstrap_servers=bootstrap_servers
                        )
                        
                        # 3b. Зарегистрировать в менеджере
                        success = await register_consumer_task(
                            manager=manager,
                            channel_id=channel_id,
                            consumer=consumer
                        )
                        
                        if success:
                            created_count += 1
                            logger.debug(
                                f"Created consumer for channel {channel_id}"
                            )
                        else:
                            logger.warning(
                                f"Failed to register consumer for channel {channel_id}"
                            )
                            await consumer.stop()
                            failed_channels.append(channel_id)
                
                except Exception as exc:
                    logger.error(
                        f"Failed to create consumer for channel {channel_id}: {exc}"
                    )
                    failed_channels.append(channel_id)
                    continue
            
            logger.info(
                f"Initialized {created_count}/{len(channels)} consumers "
                f"(failed: {len(failed_channels)})"
            )
            
            logfire.info(
                "Consumers initialized",
                created=created_count,
                total_channels=len(channels),
                failed=len(failed_channels)
            )
            
            if failed_channels:
                logfire.warning(
                    "Some consumers failed to initialize",
                    failed_channel_ids=failed_channels
                )
            
            return created_count
            
        except Exception as exc:
            logger.exception(
                f"Unexpected error in initialize_consumers_action: {exc}"
            )
            return 0

