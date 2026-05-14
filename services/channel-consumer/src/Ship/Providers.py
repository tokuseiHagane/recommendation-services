"""
Dishka Dependency Injection providers for Social Channel Consumer.

This module configures DI for both Telegram and VK modules.
"""
from dishka import Provider, make_container, Scope
from piccolo.engine.postgres import PostgresEngine

from src.Ship.config.settings import Settings, settings
from src.Ship.config.kafka_config import KafkaConfig
from src.Ship.utils.kafka_client import create_kafka_consumer
from src.Ship.utils.db import get_tg_db_engine, get_vk_db_engine


class AppProvider(Provider):
    """
    Application-level dependency provider.
    
    Provides shared infrastructure components:
    - Settings
    - Kafka configuration
    - Database engines for both TG and VK
    """
    
    def __init__(self):
        super().__init__(scope=Scope.APP)
    
    @staticmethod
    def provide_settings() -> Settings:
        """Provide global application settings."""
        return settings
    
    @staticmethod
    def provide_kafka_config() -> KafkaConfig:
        """Provide Kafka configuration."""
        return KafkaConfig()
    
    @staticmethod
    def provide_kafka_consumer():
        """Provide Kafka consumer factory."""
        # Return a factory; worker controls start/stop lifecycle
        return create_kafka_consumer
    
    @staticmethod
    def provide_tg_db_engine() -> PostgresEngine:
        """Provide Telegram database engine."""
        return get_tg_db_engine()
    
    @staticmethod
    def provide_vk_db_engine() -> PostgresEngine:
        """Provide VK database engine."""
        return get_vk_db_engine()


# Create DI container with providers
container = make_container(AppProvider())


