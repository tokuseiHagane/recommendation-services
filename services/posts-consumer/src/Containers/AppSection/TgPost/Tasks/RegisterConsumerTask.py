"""
RegisterConsumerTask: Регистрация консьюмера в менеджере.

Porto Architecture Task:
- Атомарная операция регистрации
- Делегирует к DynamicConsumerManager.add_consumer()
"""

from typing import Any
from aiokafka import AIOKafkaConsumer
import logging

logger = logging.getLogger(__name__)


async def register_consumer_task(
    manager: Any,  # DynamicConsumerManager
    channel_id: int,
    consumer: AIOKafkaConsumer
) -> bool:
    """
    Task: Зарегистрировать консьюмер в менеджере.
    
    Atomic operation для добавления консьюмера в DynamicConsumerManager.
    
    Args:
        manager: DynamicConsumerManager instance (DI)
        channel_id: ID канала
        consumer: AIOKafkaConsumer instance
    
    Returns:
        True если зарегистрирован, False если уже существует
        
    Example:
        >>> manager = DynamicConsumerManager(...)
        >>> consumer = AIOKafkaConsumer(...)
        >>> await consumer.start()
        >>> success = await register_consumer_task(manager, 123, consumer)
        >>> success
        True
    """
    
    success = await manager.add_consumer(channel_id, consumer)
    
    if success:
        logger.info(f"Registered consumer for channel {channel_id}")
    else:
        logger.warning(f"Consumer for channel {channel_id} already exists")
    
    return success

