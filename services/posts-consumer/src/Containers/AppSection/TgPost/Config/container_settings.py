"""
TgPost Container Settings: Конфигурация контейнера.
"""

from dataclasses import dataclass
import os


@dataclass
class TgPostContainerSettings:
    """
    Конфигурация контейнера TgPost.
    
    Все настройки загружаются из переменных окружения.
    """
    # Kafka settings
    kafka_bootstrap_servers: str = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS",
        "localhost:9092"
    )
    kafka_group_id_prefix: str = os.getenv(
        "KAFKA_GROUP_ID_PREFIX",
        "posts-consumer-group"
    )
    
    # Batch processing settings
    batch_size: int = int(os.getenv("BATCH_SIZE", "100"))
    batch_timeout_ms: int = int(os.getenv("BATCH_TIMEOUT_MS", "10000"))
    
    # Cache settings
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    
    # Consumer settings
    consumer_timeout_ms: int = int(os.getenv("CONSUMER_TIMEOUT_MS", "1000"))
    auto_offset_reset: str = os.getenv("AUTO_OFFSET_RESET", "earliest")


# Singleton instance
container_settings = TgPostContainerSettings()
