"""
RegisterConsumerTask: Регистрация VK консьюмера в менеджере.

Porto Architecture Task:
- Атомарная операция регистрации
- Делегирует к VkDynamicConsumerManager.add_consumer()
"""

from aiokafka import AIOKafkaConsumer
from typing import Any
import logging

logger = logging.getLogger(__name__)


async def register_consumer_task(
    manager: Any,  # VkDynamicConsumerManager
    group_id: int,
    consumer: AIOKafkaConsumer
) -> bool:
    """
    Task: Зарегистрировать VK консьюмер в менеджере.
    
    Atomic operation для регистрации консьюмера в VkDynamicConsumerManager.
    
    Args:
        manager: VkDynamicConsumerManager instance (DI)
        group_id: ID VK группы
        consumer: AIOKafkaConsumer instance
    
    Returns:
        True если консьюмер успешно зарегистрирован, False если уже существует
        
    Example:
        >>> manager = VkDynamicConsumerManager("localhost:9092", cache)
        >>> consumer = AIOKafkaConsumer(...)
        >>> success = await register_consumer_task(manager, 123, consumer)
        >>> success
        True
    """
    
    success = await manager.add_consumer(group_id, consumer)
    
    if success:
        logger.info(f"Registered VK consumer for group {group_id}")
    else:
        logger.warning(f"Failed to register VK consumer for group {group_id} (duplicate)")
    
    return success
