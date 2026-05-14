from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Global application settings."""

    # Application
    APP_NAME: str = "vk-channel-consumer"
    ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)

    # Telegram Database (PostgreSQL)
    TG_DB_HOST: str = Field(default="localhost", alias="DB_HOST")
    TG_DB_PORT: int = Field(default=5432, alias="DB_PORT")
    TG_DB_USER: str = Field(default="postgres", alias="DB_USER")
    TG_DB_PASSWORD: str = Field(default="postgres", alias="DB_PASSWORD")
    TG_DB_NAME: str = Field(default="telegram", alias="DB_NAME")

    # VK Database (PostgreSQL) - separate database for VK groups
    VK_DB_HOST: str = Field(default="localhost")
    VK_DB_PORT: int = Field(default=5432)
    VK_DB_USER: str = Field(default="postgres")
    VK_DB_PASSWORD: str = Field(default="postgres")
    VK_DB_NAME: str = Field(default="vk")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str
    
    # Telegram Kafka settings
    TG_KAFKA_TOPIC: str = Field(default="tg_channels", alias="KAFKA_TOPIC")
    TG_KAFKA_GROUP_ID: str = Field(default="tg-channel-consumer", alias="KAFKA_GROUP_ID")
    
    # VK Kafka settings
    VK_KAFKA_TOPIC: str = Field(default="vk_groups")
    VK_KAFKA_GROUP_ID: str = Field(default="vk-group-consumer")

    # Batch Processing
    BATCH_SIZE: int = Field(default=100, description="Number of messages to accumulate before batch insert")
    BATCH_TIMEOUT: float = Field(default=5.0, description="Max seconds to wait before flushing incomplete batch")

    # Other
    LOG_LEVEL: str = Field(default="INFO")
    
    # Module toggles for distributed monolith
    ENABLE_TG_MODULE: bool = Field(default=True, description="Enable Telegram channel processing module")
    ENABLE_VK_MODULE: bool = Field(default=True, description="Enable VK group processing module")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", populate_by_name=True)

    @property
    def tg_database_url(self) -> str:
        """Build a Postgres DSN string for Telegram database."""
        return f"postgresql+asyncpg://{self.TG_DB_USER}:{self.TG_DB_PASSWORD}@{self.TG_DB_HOST}:{self.TG_DB_PORT}/{self.TG_DB_NAME}"

    @property
    def vk_database_url(self) -> str:
        """Build a Postgres DSN string for VK database."""
        return f"postgresql+asyncpg://{self.VK_DB_USER}:{self.VK_DB_PASSWORD}@{self.VK_DB_HOST}:{self.VK_DB_PORT}/{self.VK_DB_NAME}"

    # Backward compatibility alias
    @property
    def database_url(self) -> str:
        """Build a Postgres DSN string for Piccolo ORM (Telegram DB for backward compatibility)."""
        return self.tg_database_url


# Instantiate a global settings object
settings = Settings()
