from dataclasses import dataclass
from .settings import settings


@dataclass
class KafkaConfig:
    """Kafka configuration dataclass."""

    bootstrap_servers: str = settings.KAFKA_BOOTSTRAP_SERVERS
    # Keep generic defaults mapped to the Telegram module for backward
    # compatibility. VK workers override topic / group_id explicitly.
    topic: str = settings.TG_KAFKA_TOPIC
    group_id: str = settings.TG_KAFKA_GROUP_ID
    enable_auto_commit: bool = True
    auto_offset_reset: str = "earliest"
    consumer_timeout_ms: int = 1000
