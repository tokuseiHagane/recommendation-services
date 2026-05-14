"""
ConsumePostsBatchTask: Чтение батча сообщений из Kafka.

Porto Architecture Task:
- Атомарная операция чтения из Kafka
- Использование getmany для batch consumption
- Парсинг JSON с error handling
"""

from typing import Dict, Any, List
import json
from aiokafka import AIOKafkaConsumer
import logging

logger = logging.getLogger(__name__)


async def consume_posts_batch_task(
    consumer: AIOKafkaConsumer,
    batch_size: int = 100,
    timeout_ms: int = 10000
) -> List[Dict[str, Any]]:
    """
    Task: Consume батч постов из Kafka.
    
    Atomic operation для чтения батча сообщений через getmany().
    Парсит JSON и ограничивает размер батча.
    
    Args:
        consumer: AIOKafkaConsumer instance
        batch_size: Максимальный размер батча
        timeout_ms: Timeout для getmany (milliseconds)
    
    Returns:
        Список сообщений (parsed from JSON)
        
    Example:
        >>> consumer = AIOKafkaConsumer(...)
        >>> await consumer.start()
        >>> messages = await consume_posts_batch_task(
        ...     consumer=consumer,
        ...     batch_size=100,
        ...     timeout_ms=10000
        ... )
        >>> len(messages)
        100
    """
    
    messages = []
    
    # Batch consumption с getmany
    # Возвращает Dict[TopicPartition, List[ConsumerRecord]]
    result = await consumer.getmany(timeout_ms=timeout_ms)
    
    for tp, msgs in result.items():
        for msg in msgs:
            try:
                # Parse JSON
                post_data = json.loads(msg.value.decode('utf-8'))
                messages.append(post_data)
                
                if len(messages) >= batch_size:
                    break
                    
            except json.JSONDecodeError as exc:
                logger.warning(f"Failed to parse JSON message: {exc}")
                continue
            except Exception as exc:
                logger.warning(f"Failed to process message: {exc}")
                continue
        
        if len(messages) >= batch_size:
            break
    
    logger.debug(f"Consumed {len(messages)} messages from Kafka")
    
    return messages[:batch_size]

