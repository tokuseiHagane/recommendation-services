from dataclasses import dataclass
from .settings import settings


@dataclass
class KafkaConfig:
    """Kafka configuration dataclass."""

    bootstrap_servers: str = settings.KAFKA_BOOTSTRAP_SERVERS
    topic: str = settings.KAFKA_TOPIC
    group_id: str = settings.KAFKA_GROUP_ID
    enable_auto_commit: bool = True
    auto_offset_reset: str = "earliest"
    consumer_timeout_ms: int = 1000
