"""
CreateKafkaConsumerTask: Создание и запуск AIOKafkaConsumer для VK.

Porto Architecture Task:
- Атомарная операция создания консьюмера
- Конфигурация для топика vk_posts_{group_id}
- Manual commit для at-least-once семантики
"""

from aiokafka import AIOKafkaConsumer
import logging

from src.Containers.AppSection.VkPost.Exceptions.ConsumerCreationException import ConsumerCreationException

logger = logging.getLogger(__name__)


async def create_kafka_consumer_task(
    group_id: int,
    bootstrap_servers: str,
    group_id_prefix: str = "vk-posts-consumer-group",
    topic_prefix: str = "vk_posts_"
) -> AIOKafkaConsumer:
    """
    Task: Создать Kafka consumer для VK группы.
    
    Atomic operation для создания и запуска AIOKafkaConsumer.
    Конфигурация:
    - enable_auto_commit=False для manual commit
    - auto_offset_reset="earliest" для обработки с начала
    - consumer_timeout_ms=1000 для getmany timeout
    
    Args:
        group_id: ID VK группы
        bootstrap_servers: Kafka bootstrap servers
        group_id_prefix: Префикс для consumer group ID
        topic_prefix: Префикс для топика (default: vk_posts_)
    
    Returns:
        Запущенный AIOKafkaConsumer
        
    Raises:
        ConsumerCreationException: Если не удалось создать/запустить
        
    Example:
        >>> consumer = await create_kafka_consumer_task(
        ...     group_id=123,
        ...     bootstrap_servers="localhost:9092"
        ... )
        >>> # consumer готов к использованию
    """
    
    topic = f"{topic_prefix}{group_id}"
    consumer_group_id = f"{group_id_prefix}-{group_id}"
    
    try:
        # Explicit session/heartbeat/max-poll settings.
        # Defaults (session=10s, heartbeat=3s) are aggressive and combined with
        # brief duplicate consumer appearances caused a constant rebalance loop.
        session_timeout_ms = 30_000
        heartbeat_interval_ms = 10_000
        max_poll_interval_ms = 300_000

        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=consumer_group_id,
            enable_auto_commit=False,  # Manual commit для at-least-once
            auto_offset_reset="earliest",  # Начать с начала если offset не найден
            consumer_timeout_ms=1000,  # Timeout для getmany
            session_timeout_ms=session_timeout_ms,
            heartbeat_interval_ms=heartbeat_interval_ms,
            max_poll_interval_ms=max_poll_interval_ms,
        )

        logger.info(
            "Creating Kafka consumer: topic=%s, group_id=%s, "
            "session_timeout_ms=%s, heartbeat_interval_ms=%s, max_poll_interval_ms=%s",
            topic,
            consumer_group_id,
            session_timeout_ms,
            heartbeat_interval_ms,
            max_poll_interval_ms,
        )

        await consumer.start()

        logger.info(f"Created VK consumer for {topic} with group {consumer_group_id}")
        
        return consumer
        
    except Exception as exc:
        logger.exception(f"Failed to create VK consumer for group {group_id}: {exc}")
        raise ConsumerCreationException(
            f"Failed to create VK consumer for group {group_id}: {exc}"
        )
