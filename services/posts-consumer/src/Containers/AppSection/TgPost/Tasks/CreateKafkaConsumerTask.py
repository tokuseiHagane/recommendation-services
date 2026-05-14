"""
CreateKafkaConsumerTask: Создание и запуск AIOKafkaConsumer.

Porto Architecture Task:
- Атомарная операция создания консьюмера
- Конфигурация для топика tg_posts_{id}
- Manual commit для at-least-once семантики
"""

from aiokafka import AIOKafkaConsumer
import logging

from src.Containers.AppSection.TgPost.Exceptions.ConsumerCreationException import ConsumerCreationException

logger = logging.getLogger(__name__)


async def create_kafka_consumer_task(
    channel_id: int,
    bootstrap_servers: str,
    group_id_prefix: str = "posts-consumer-group"
) -> AIOKafkaConsumer:
    """
    Task: Создать Kafka consumer для канала.
    
    Atomic operation для создания и запуска AIOKafkaConsumer.
    Конфигурация:
    - enable_auto_commit=False для manual commit
    - auto_offset_reset="earliest" для обработки с начала
    - consumer_timeout_ms=1000 для getmany timeout
    
    Args:
        channel_id: ID канала
        bootstrap_servers: Kafka bootstrap servers
        group_id_prefix: Префикс для consumer group ID
    
    Returns:
        Запущенный AIOKafkaConsumer
        
    Raises:
        ConsumerCreationException: Если не удалось создать/запустить
        
    Example:
        >>> consumer = await create_kafka_consumer_task(
        ...     channel_id=123,
        ...     bootstrap_servers="localhost:9092"
        ... )
        >>> # consumer готов к использованию
    """
    
    topic = f"tg_posts_{channel_id}"
    group_id = f"{group_id_prefix}-{channel_id}"
    
    try:
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=False,  # Manual commit для at-least-once
            auto_offset_reset="earliest",  # Начать с начала если offset не найден
            consumer_timeout_ms=1000  # Timeout для getmany
        )
        
        await consumer.start()
        
        logger.info(f"Created consumer for {topic} with group {group_id}")
        
        return consumer
        
    except Exception as exc:
        logger.exception(f"Failed to create consumer for channel {channel_id}: {exc}")
        raise ConsumerCreationException(
            f"Failed to create consumer for channel {channel_id}: {exc}"
        )

