"""
ConsumerCreationException: Ошибка создания Kafka consumer.
"""


class ConsumerCreationException(Exception):
    """
    Exception: Ошибка создания Kafka consumer.
    
    Использование:
    - Raise в CreateKafkaConsumerTask при ошибке создания/запуска
    - Catch в CreateDynamicConsumerAction для логирования
    """
    pass
