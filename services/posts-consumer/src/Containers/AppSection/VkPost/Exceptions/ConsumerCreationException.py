"""
ConsumerCreationException: Исключение для ошибок создания VK консьюмера.

Porto Architecture Exception:
- Наследует от Exception
- Используется в CreateKafkaConsumerTask
"""


class ConsumerCreationException(Exception):
    """
    Exception для ошибок создания Kafka консьюмера для VK.
    
    Возникает когда:
    - Не удалось подключиться к Kafka
    - Ошибка конфигурации консьюмера
    - Timeout при запуске
    
    Example:
        >>> try:
        ...     consumer = await create_kafka_consumer_task(group_id, servers)
        ... except ConsumerCreationException as exc:
        ...     logger.error(f"Consumer creation failed: {exc}")
    """
    pass
