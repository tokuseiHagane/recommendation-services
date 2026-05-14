"""Application configuration module."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = Field(default="vk-parser-service", description="Application name")
    app_env: str = Field(default="development", description="Application environment")
    app_debug: bool = Field(default=True, description="Debug mode")
    app_host: str = Field(default="0.0.0.0", description="Application host")
    api_version: str = Field(default="v1", env="API_VERSION", description="API version")
    service_name: str = Field(default="vk", env="SERVICE_NAME", description="Service name")
    app_port: int = Field(default=8000, description="Application port")

    # Database (shared with AuthorizationService)
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/porto_db",
        description="PostgreSQL database connection URL",
    )

    # Logfire
    logfire_token: str | None = Field(default=None, description="Logfire token")
    logfire_project_name: str = Field(default="vk-parser-service", description="Logfire project name")
    logfire_environment: str = Field(default="development", description="Logfire environment")
    logfire_log_level: str = Field(default="INFO", description="Logfire logging level")
    logfire_sample_rate: float = Field(default=1.0, description="Logfire sampling rate (0.0-1.0)")

    # Legacy JWT settings kept for transition period documentation.
    # The primary auth flow now uses Bearer JWT + JWKS verification.
    jwt_secret_key: str = Field(default="your-jwt-secret-here", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")

    # AuthService integration
    auth_service_url: str = Field(default="http://localhost:3000", description="Internal AuthService base URL")
    auth_jwks_url: str | None = Field(default=None, description="Explicit JWKS URL override")
    auth_jwt_issuer: str = Field(default="fdauth-service", description="Expected JWT issuer")
    # Better Auth JWT-плагин всегда проставляет `aud` в payload (см. JWT_AUDIENCE в AuthServiceElysia).
    # PyJWT 2.10+ при наличии `aud` в токене требует явно передать ожидаемый audience в `decode`
    # — иначе падает InvalidAudienceError("Invalid audience"). Поэтому настройка обязательна,
    # когда auth-сервис подписывает токены с audience.
    auth_jwt_audience: str | None = Field(
        default="fdauth-integrations",
        description="Expected JWT audience (must match Better Auth JWT_AUDIENCE)",
    )
    auth_jwt_algorithms: list[str] = Field(default_factory=lambda: ["RS256"], description="Allowed JWT algorithms")
    auth_jwt_leeway_seconds: int = Field(default=30, description="Clock skew leeway for JWT validation")
    auth_jwks_cache_ttl_seconds: int = Field(default=300, description="JWKS cache TTL in seconds")
    auth_vk_token_endpoint: str = Field(
        default="/api/internal/auth/vk-account",
        description="AuthService endpoint returning current user's VK account metadata (auto-refreshes expiring tokens)",
    )
    auth_vk_refresh_endpoint: str = Field(
        default="/api/internal/auth/vk-account/refresh",
        description="AuthService endpoint for forcing a VK access_token refresh (POST)",
    )
    auth_backend_shared_secret: str | None = Field(
        default=None,
        description="Shared secret for internal AuthService backend endpoints",
    )
    auth_http_timeout_seconds: float = Field(default=5.0, description="Internal AuthService request timeout")
    auth_enable_legacy_cookie_fallback: bool = Field(
        default=False,
        description="Allow temporary fallback to auth_token cookie when Authorization header is missing",
    )
    auth_enable_legacy_db_fallback: bool = Field(
        default=False,
        description="Allow temporary fallback to AccountTokens table when AuthService token endpoint is unavailable",
    )

    # VK API (fallback token for testing)
    vk_access_token: str | None = Field(default=None, description="Fallback VK API access token")

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_default_ttl: int = Field(
        default=86400,
        description="Default cache TTL in seconds",
    )

    # Kafka
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers",
    )
    kafka_groups_topic: str = Field(
        default="vk_groups",
        description="Kafka topic for VK group metadata",
    )
    kafka_posts_topic_prefix: str = Field(
        default="vk_posts_",
        description="Kafka topic prefix for VK posts (appended with group_id)",
    )

    # Rate limiting (in-memory, per-replica — see design doc §3).
    rate_limit_global_per_minute: int = Field(
        default=60,
        description="Global per-IP HTTP rate limit (requests per minute).",
    )
    rate_limit_parse_per_minute: int = Field(
        default=10,
        description="Stricter per-IP rate limit for POST /parse/vk (heavy sync parsing).",
    )
    rate_limit_search_per_minute: int = Field(
        default=30,
        description="Stricter per-IP rate limit for GET /search/vk.",
    )
    rate_limit_ws_min_interval_ms: int = Field(
        default=300,
        description="Minimum interval between VK search WS queries per connection (ms).",
    )

    # CORS
    cors_allow_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_allow_methods: list[str] = Field(default=["*"], description="Allowed CORS methods")
    cors_allow_headers: list[str] = Field(default=["*"], description="Allowed CORS headers")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("auth_jwt_algorithms", mode="before")
    @classmethod
    def parse_auth_jwt_algorithms(cls, v: Any) -> list[str]:
        """Parse JWT algorithms from string or list."""
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                return json.loads(v)
            return [algorithm.strip() for algorithm in v.split(",") if algorithm.strip()]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env == "development"

    @property
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent.parent

    @property
    def resolved_auth_jwks_url(self) -> str:
        """Resolve JWKS URL from explicit override or AuthService base URL."""
        if self.auth_jwks_url:
            return self.auth_jwks_url
        return f"{self.auth_service_url.rstrip('/')}/api/auth/jwks"

    @property
    def resolved_auth_vk_token_url(self) -> str:
        """Resolve internal VK token endpoint URL."""
        return f"{self.auth_service_url.rstrip('/')}/{self.auth_vk_token_endpoint.lstrip('/')}"

    @property
    def resolved_auth_vk_refresh_url(self) -> str:
        """Resolve internal VK token force-refresh endpoint URL."""
        return f"{self.auth_service_url.rstrip('/')}/{self.auth_vk_refresh_endpoint.lstrip('/')}"


@lru_cache
def get_settings() -> AppSettings:
    """Get cached application settings."""
    return AppSettings()
