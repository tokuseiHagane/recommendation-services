"""
CreateDynamicVkConsumerAction: Реактивное создание VK консьюмера.

Porto Architecture Action:
- Оркестрирует CheckDuplicateTask → UpdateCacheTask → CreateKafkaConsumerTask → RegisterConsumerTask
- Logfire трассировка для observability
- Error handling с ConsumerCreationException
"""

from typing import Dict, Any, Optional
from aiokafka import AIOKafkaConsumer
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

from src.Containers.AppSection.VkPost.Tasks.CheckDuplicateTask import check_duplicate_task
from src.Containers.AppSection.VkPost.Tasks.UpdateCacheTask import update_cache_task
from src.Containers.AppSection.VkPost.Tasks.CreateKafkaConsumerTask import create_kafka_consumer_task
from src.Containers.AppSection.VkPost.Tasks.RegisterConsumerTask import register_consumer_task
from src.Containers.AppSection.VkPost.Exceptions.ConsumerCreationException import ConsumerCreationException

logger = logging.getLogger(__name__)


async def create_dynamic_vk_consumer_action(
    *,
    group_data: Dict[str, Any],
    cache: Any,  # VkGroupsCache
    manager: Any,  # VkDynamicConsumerManager
    bootstrap_servers: str,
    topic_prefix: str = "vk_posts_"
) -> Optional[AIOKafkaConsumer]:
    """
    Action: Реактивно создать VK консьюмер для новой группы.
    
    Бизнес use case для создания консьюмера при получении события из vk_groups_diff.
    Оркестрирует:
    1. CheckDuplicateTask - проверка наличия в кэше
    2. UpdateCacheTask - добавление группы в кэш
    3. CreateKafkaConsumerTask - создание консьюмера
    4. RegisterConsumerTask - регистрация в менеджере
    
    Args:
        group_data: Данные VK группы из vk_groups_diff
        cache: VkGroupsCache instance (DI)
        manager: VkDynamicConsumerManager instance (DI)
        bootstrap_servers: Kafka bootstrap servers
        topic_prefix: Префикс для VK топиков
    
    Returns:
        AIOKafkaConsumer instance или None если уже существует
        
    Raises:
        ConsumerCreationException: Если не удалось создать консьюмер
        
    Example:
        >>> group_data = {"id": 123, "name": "Tech News", "screen_name": "technews"}
        >>> consumer = await create_dynamic_vk_consumer_action(
        ...     group_data=group_data,
        ...     cache=cache,
        ...     manager=manager,
        ...     bootstrap_servers="localhost:9092"
        ... )
    """
    
    group_id = group_data.get("id")
    
    if not group_id:
        logger.warning("Group data without id, cannot create consumer")
        return None
    
    with logfire.span(
        "create_dynamic_vk_consumer_action",
        group_id=group_id
    ):
        try:
            # 1. Проверка дубликата
            with logfire.span("check_duplicate"):
                is_duplicate = await check_duplicate_task(cache, group_id)
                
                if is_duplicate:
                    logger.info(f"VK Group {group_id} already exists, skipping")
                    logfire.info(
                        "VK Group already exists",
                        group_id=group_id
                    )
                    return None
            
            # 2. Добавление в кэш
            with logfire.span("update_cache"):
                await update_cache_task(cache, [group_data])
                logger.debug(f"Added VK group {group_id} to cache")
            
            # 3. Создание консьюмера
            with logfire.span("create_consumer"):
                consumer = await create_kafka_consumer_task(
                    group_id=group_id,
                    bootstrap_servers=bootstrap_servers,
                    topic_prefix=topic_prefix
                )
                logger.info(f"Created VK consumer for group {group_id}")
            
            # 4. Регистрация в менеджере
            with logfire.span("register_consumer"):
                success = await register_consumer_task(
                    manager=manager,
                    group_id=group_id,
                    consumer=consumer
                )
                
                if not success:
                    logger.warning(
                        f"Failed to register VK consumer for group {group_id}, stopping"
                    )
                    await consumer.stop()
                    return None
            
            logfire.info(
                "VK Consumer created dynamically",
                group_id=group_id
            )
            
            return consumer
            
        except ConsumerCreationException as exc:
            logger.exception(
                f"Failed to create VK consumer for group {group_id}: {exc}"
            )
            logfire.warning(
                "VK Consumer creation failed",
                group_id=group_id,
                error=str(exc)
            )
            raise
        
        except Exception as exc:
            logger.exception(
                f"Unexpected error creating VK consumer for group {group_id}: {exc}"
            )
            return None
