from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
from src.Ship.config.settings import settings as global_settings


class ContainerSettings(BaseSettings):
    """
    Container-specific overrides. Values come from env first, then fallback
    to global ship settings where appropriate.
    """

    # If you want container-specific topic override
    KAFKA_TOPIC: Optional[str] = Field(default=None)

    # local tuning
    MAX_RETRIES: int = Field(default=3)
    RETRY_BACKOFF_SECONDS: int = Field(default=2)
    PROCESSING_CONCURRENCY: int = Field(default=5)

    # For convenience, expose DB / Kafka settings used by this container
    DB_NAME: str = Field(default=global_settings.DB_NAME)
    DB_USER: str = Field(default=global_settings.DB_USER)
    DB_HOST: str = Field(default=global_settings.DB_HOST)
    DB_PORT: int = Field(default=global_settings.DB_PORT)

    model_config = {
        "env_prefix": "MESSAGES_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @property
    def kafka_topic(self) -> str:
        return self.KAFKA_TOPIC or global_settings.KAFKA_TOPIC


container_settings = ContainerSettings()

