from aiokafka import AIOKafkaConsumer
from src.Ship.config.kafka_config import KafkaConfig


def create_kafka_consumer() -> AIOKafkaConsumer:
    """Factory function to create a configured Kafka consumer."""
    conf = KafkaConfig()
    consumer = AIOKafkaConsumer(
        conf.topic,
        bootstrap_servers=conf.bootstrap_servers,
        group_id=conf.group_id,
        enable_auto_commit=conf.enable_auto_commit,
        auto_offset_reset=conf.auto_offset_reset,
        consumer_timeout_ms=conf.consumer_timeout_ms,
    )
    return consumer
