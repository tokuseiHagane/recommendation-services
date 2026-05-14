from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # Postgres
    postgres_user: str = Field(..., env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    postgres_db: str = Field(..., env="POSTGRES_DB")
    postgres_host: str = Field(..., env="POSTGRES_HOST")
    postgres_port: int = Field(..., env="POSTGRES_PORT")

    # Kafka / RedPanda
    kafka_bootstrap: str = Field(..., env="KAFKA_BROKER")
    kafka_topic: str = Field(..., env="KAFKA_TOPIC")
    kafka_group: str = Field(..., env="KAFKA_GROUP")

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"

settings = Settings()
