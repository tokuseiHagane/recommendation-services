"""
VkPost Container Settings: Конфигурация контейнера.
"""

from dataclasses import dataclass
import os


@dataclass
class VkPostContainerSettings:
    """
    Конфигурация контейнера VkPost.
    
    Все настройки загружаются из переменных окружения.
    """
    # Kafka settings
    kafka_bootstrap_servers: str = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS",
        "localhost:9092"
    )
    kafka_group_id_prefix: str = os.getenv(
        "KAFKA_GROUP_ID_PREFIX",
        "vk-posts-consumer-group"
    )
    kafka_groups_diff_topic: str = os.getenv(
        "KAFKA_GROUPS_DIFF_TOPIC",
        "vk_groups_diff"
    )
    kafka_posts_topic_prefix: str = os.getenv(
        "KAFKA_POSTS_TOPIC_PREFIX",
        "vk_posts_"
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
container_settings = VkPostContainerSettings()
