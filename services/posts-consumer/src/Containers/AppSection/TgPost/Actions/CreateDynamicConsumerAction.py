"""
CreateDynamicConsumerAction: Реактивное создание нового консьюмера.

Porto Architecture Action:
- Оркестрирует CheckDuplicateTask → UpdateCacheTask → CreateKafkaConsumerTask → RegisterConsumerTask
- Logfire трассировка для observability
- Error handling с ConsumerCreationException
"""

from typing import Dict, Any, Optional
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

from src.Containers.AppSection.TgPost.Tasks.CheckDuplicateTask import check_duplicate_task
from src.Containers.AppSection.TgPost.Tasks.UpdateCacheTask import update_cache_task
from src.Containers.AppSection.TgPost.Tasks.CreateKafkaConsumerTask import create_kafka_consumer_task
from src.Containers.AppSection.TgPost.Tasks.RegisterConsumerTask import register_consumer_task
from src.Containers.AppSection.TgPost.Exceptions.ConsumerCreationException import ConsumerCreationException

logger = logging.getLogger(__name__)


async def create_dynamic_consumer_action(
    channel_data: Dict[str, Any],
    *,
    cache: Any,  # PostObjectsCache
    manager: Any,  # DynamicConsumerManager
    bootstrap_servers: str
) -> Optional[int]:
    """
    Action: Создать новый консьюмер для канала.
    
    Бизнес use case для реактивного создания консьюмера при получении события о новом канале.
    Оркестрирует:
    1. CheckDuplicateTask - проверка наличия в кэше
    2. UpdateCacheTask - добавление канала в кэш
    3. CreateKafkaConsumerTask - создание AIOKafkaConsumer
    4. RegisterConsumerTask - регистрация в менеджере
    
    Args:
        channel_data: Данные о канале из tg_channels_diff
            Expected keys: id, name, type
        cache: PostObjectsCache instance (DI)
        manager: DynamicConsumerManager instance (DI)
        bootstrap_servers: Kafka bootstrap servers
    
    Returns:
        Channel ID если консьюмер создан, None если уже существует
        
    Raises:
        ConsumerCreationException: Если не удалось создать консьюмер
        
    Example:
        >>> channel_data = {"id": 123, "name": "Tech", "type": "public"}
        >>> channel_id = await create_dynamic_consumer_action(
        ...     channel_data,
        ...     cache=cache,
        ...     manager=manager,
        ...     bootstrap_servers="localhost:9092"
        ... )
        >>> channel_id
        123
    """
    
    channel_id = channel_data.get("id")
    channel_name = channel_data.get("name", "Unknown")
    
    if not channel_id:
        logger.error("Channel data missing id field")
        return None
    
    with logfire.span(
        "create_dynamic_consumer_action",
        channel_id=channel_id,
        channel_name=channel_name
    ):
        try:
            # 1. Проверка дубликата
            with logfire.span("check_duplicate"):
                is_duplicate = await check_duplicate_task(cache, channel_id)
                
                if is_duplicate:
                    logger.warning(
                        f"Channel {channel_id} already exists, skipping"
                    )
                    logfire.warning(
                        "Duplicate channel",
                        channel_id=channel_id
                    )
                    return None
            
            # 2. Обновление кэша
            with logfire.span("update_cache"):
                await update_cache_task(cache, [channel_data])
                logger.info(f"Added channel {channel_id} to cache")
            
            # 3. Создание Kafka консьюмера
            with logfire.span("create_kafka_consumer"):
                consumer = await create_kafka_consumer_task(
                    channel_id=channel_id,
                    bootstrap_servers=bootstrap_servers
                )
                logger.info(f"Created Kafka consumer for channel {channel_id}")
            
            # 4. Регистрация в менеджере
            with logfire.span("register_consumer"):
                success = await register_consumer_task(
                    manager=manager,
                    channel_id=channel_id,
                    consumer=consumer
                )
                
                if not success:
                    logger.error(
                        f"Failed to register consumer for channel {channel_id}"
                    )
                    # Остановить консьюмер если не удалось зарегистрировать
                    await consumer.stop()
                    return None
            
            logger.info(
                f"Successfully created dynamic consumer for channel {channel_id}"
            )
            logfire.info(
                "Consumer created",
                channel_id=channel_id,
                channel_name=channel_name
            )
            
            return channel_id
            
        except ConsumerCreationException as exc:
            logger.exception(
                f"Failed to create consumer for channel {channel_id}: {exc}"
            )
            logfire.info(
                "Consumer creation failed",
                channel_id=channel_id,
                error=str(exc)
            )
            raise
        
        except Exception as exc:
            logger.exception(
                f"Unexpected error in create_dynamic_consumer_action "
                f"for channel {channel_id}: {exc}"
            )
            return None

