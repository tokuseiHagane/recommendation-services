from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "case_sensitive": False}

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/recsys_test"
    REDIS_URL: str = "redis://localhost:6379/0"
    OPENSEARCH_URL: str = "http://localhost:9200"
    POLLING_INTERVAL_SECONDS: int = 300


settings = Settings()
