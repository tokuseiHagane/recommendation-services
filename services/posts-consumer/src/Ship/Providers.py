from dishka import Provider, make_container, Scope

from src.Ship.config.settings import settings
from src.Ship.config.kafka_config import KafkaConfig
from src.Ship.utils.kafka_client import create_kafka_consumer


class AppProvider(Provider):
    """Application-level dependency provider."""
    
    def __init__(self):
        super().__init__(scope=Scope.APP)
    
    @staticmethod
    def provide_settings():
        return settings
    
    @staticmethod
    def provide_kafka_config() -> KafkaConfig:
        return KafkaConfig()
    
    @staticmethod
    def provide_kafka_consumer():
        # Return a factory; worker controls start/stop lifecycle
        return create_kafka_consumer


# Create DI container with providers
container = make_container(AppProvider())


