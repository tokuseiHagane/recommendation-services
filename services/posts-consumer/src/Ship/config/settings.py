from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Global application settings with multi-database support."""

    # Application
    APP_NAME: str = "message-consumer"
    ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)

    # Default Database (PostgreSQL) - used by TgPost
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = 5432
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="postgres")
    DB_NAME: str = Field(default="post_db")

    # VK Database (PostgreSQL) - separate database for VkPost
    VK_DB_HOST: str = Field(default="localhost")
    VK_DB_PORT: int = 5432
    VK_DB_USER: str = Field(default="postgres")
    VK_DB_PASSWORD: str = Field(default="postgres")
    VK_DB_NAME: str = Field(default="vk")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:9092")
    KAFKA_TOPIC: str | None = None  # Optional - используется только если нужен один топик
    KAFKA_GROUP_ID: str = "message-consumer-group"

    # Batch Processing
    BATCH_SIZE: int = Field(default=100, description="Number of messages to accumulate before batch insert")
    BATCH_TIMEOUT: float = Field(default=5.0, description="Max seconds to wait before flushing incomplete batch")

    # Other
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def database_url(self) -> str:
        """Build a Postgres DSN string for default (TgPost) database."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def vk_database_url(self) -> str:
        """Build a Postgres DSN string for VK database."""
        return f"postgresql+asyncpg://{self.VK_DB_USER}:{self.VK_DB_PASSWORD}@{self.VK_DB_HOST}:{self.VK_DB_PORT}/{self.VK_DB_NAME}"

    def get_db_config(self, db_name: str = "default") -> dict:
        """
        Get database configuration by name.
        
        Args:
            db_name: Database identifier ("default" for TgPost, "vk" for VkPost)
            
        Returns:
            Dictionary with database connection parameters.
        """
        if db_name == "vk":
            return {
                "database": self.VK_DB_NAME,
                "user": self.VK_DB_USER,
                "password": self.VK_DB_PASSWORD,
                "host": self.VK_DB_HOST,
                "port": self.VK_DB_PORT,
            }
        # Default database (TgPost)
        return {
            "database": self.DB_NAME,
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "host": self.DB_HOST,
            "port": self.DB_PORT,
        }


# Instantiate a global settings object
settings = Settings()
