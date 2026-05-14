"""Enhanced Logfire logging configuration for VK Parser Service."""

import logging

import logfire
from logfire import ConsoleOptions

from src.Ship.Configs.App import get_settings


class LogfireManager:
    """Manages Logfire configuration for different environments."""

    def __init__(self):
        """Initialize Logfire manager."""
        self._settings = get_settings()
        self._configured = False

    def configure(self) -> None:
        """Configure Logfire based on environment settings."""
        if self._configured:
            return

        if self._settings.logfire_token:
            self._configure_remote()
        else:
            self._configure_local()

        self._configure_auto_tracing()
        self._configured = True

    def _configure_remote(self) -> None:
        """Configure Logfire for remote logging."""
        min_log_level = self._settings.logfire_log_level.lower()
        if self._settings.is_production:
            logfire.configure(
                token=self._settings.logfire_token,
                environment=self._settings.logfire_environment,
                service_name="vk-parser-service",
                service_version="0.1.0",
                console=ConsoleOptions(
                    verbose=False,
                    include_timestamps=True,
                    min_log_level=min_log_level,
                ),
            )
            logging.getLogger().setLevel(logging.WARNING)
            logfire.info("🔥 Logfire configured for PRODUCTION", environment=self._settings.app_env, log_level="ERROR+")
        else:
            logfire.configure(
                token=self._settings.logfire_token,
                environment=self._settings.logfire_environment,
                service_name="vk-parser-service",
                service_version="0.1.0",
                console=ConsoleOptions(
                    verbose=True,
                    include_timestamps=True,
                    colors="auto",
                    min_log_level=min_log_level,
                ),
            )
            logging.getLogger().setLevel(logging.DEBUG)
            logfire.info(
                "🔥 Logfire configured for DEVELOPMENT",
                environment=self._settings.app_env,
                log_level=min_log_level.upper(),
            )

    def _configure_local(self) -> None:
        """Configure Logfire for local logging without token."""
        min_log_level = self._settings.logfire_log_level.lower()
        if self._settings.is_production:
            logfire.configure(
                send_to_logfire=False,
                console=ConsoleOptions(
                    verbose=False,
                    include_timestamps=True,
                    min_log_level=min_log_level,
                    colors="never",
                ),
            )
            logging.getLogger().setLevel(logging.WARNING)
            logfire.warning(
                "⚠️ Logfire running in LOCAL mode for PRODUCTION (no token)",
                environment=self._settings.app_env,
                log_level="ERROR+",
                recommendation="Configure LOGFIRE_TOKEN for production monitoring",
            )
        else:
            logfire.configure(
                send_to_logfire=False,
                console=ConsoleOptions(
                    verbose=True,
                    include_timestamps=True,
                    colors="auto",
                    min_log_level=min_log_level,
                ),
            )
            logging.getLogger().setLevel(logging.DEBUG)
            logfire.info(
                "🔥 Logfire running in LOCAL mode for DEVELOPMENT",
                environment=self._settings.app_env,
                log_level=min_log_level.upper(),
                recommendation="Set LOGFIRE_TOKEN to enable remote logging",
            )

    def _configure_auto_tracing(self) -> None:
        """Configure automatic tracing based on environment."""
        if self._settings.is_production:
            logfire.install_auto_tracing(
                modules=["src.Containers", "src.Ship"],
                min_duration=0.1,
                check_imported_modules="ignore",
            )
            logfire.debug(
                "🔍 Auto-tracing configured for PRODUCTION",
                min_duration="100ms",
                modules=["src.Containers", "src.Ship"],
            )
        else:
            logfire.install_auto_tracing(
                modules=["src.Containers", "src.Ship"],
                min_duration=0.05,
                check_imported_modules="warn",
            )
            logfire.debug(
                "🔍 Auto-tracing configured for DEVELOPMENT", min_duration="50ms", modules=["src.Containers", "src.Ship"]
            )


class ServiceLogger:
    """VK Parser Service specific logger with structured logging."""

    def __init__(self, name: str):
        """Initialize logger for specific component.

        Args:
            name: Logger name (usually __name__)
        """
        self._name = name
        self._settings = get_settings()

    def vk_request(self, method: str, params: dict | None = None, duration_ms: float | None = None, **kwargs) -> None:
        """Log VK API request."""
        logfire.info(
            f"📡 VK API: {method}",
            vk_method=method,
            params=params,
            duration_ms=duration_ms,
            component=self._name,
            **kwargs,
        )

    def vk_error(self, method: str, error: str, error_code: int | None = None, **kwargs) -> None:
        """Log VK API error."""
        logfire.error(
            f"❌ VK API Error: {method}",
            vk_method=method,
            error=error,
            error_code=error_code,
            component=self._name,
            **kwargs,
        )

    def parse_start(self, domains: list[str], **kwargs) -> None:
        """Log parse operation start."""
        logfire.info(
            f"🚀 Starting VK parse for {len(domains)} domains", domains=domains, component=self._name, **kwargs
        )

    def parse_complete(self, domains: list[str], duration_ms: float | None = None, **kwargs) -> None:
        """Log parse operation completion."""
        logfire.info(
            f"✅ VK parse completed for {len(domains)} domains",
            domains=domains,
            duration_ms=duration_ms,
            component=self._name,
            **kwargs,
        )

    def cache_operation(self, operation: str, key: str, hit: bool, duration_ms: float | None = None, **kwargs) -> None:
        """Log cache operations."""
        if self._settings.is_development or not hit:
            logfire.debug(
                f"📦 Cache {operation}",
                operation=operation,
                cache_key=key,
                cache_hit=hit,
                duration_ms=duration_ms,
                component=self._name,
                **kwargs,
            )

    def api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> None:
        """Log API requests."""
        if status_code >= 400:
            log_level = "error" if status_code >= 500 else "warning"
        else:
            log_level = "info" if self._settings.is_development else "debug"

        log_func = getattr(logfire, log_level)
        log_func(
            f"🌐 {method} {path} - {status_code}",
            http_method=method,
            http_path=path,
            http_status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            component=self._name,
            **kwargs,
        )


# Global instances
logfire_manager = LogfireManager()


def get_service_logger(name: str) -> ServiceLogger:
    """Get VK Parser Service logger for component.

    Args:
        name: Component name (usually __name__)

    Returns:
        Configured ServiceLogger instance
    """
    return ServiceLogger(name)


def configure_logging() -> None:
    """Configure logging for the VK Parser Service."""
    logfire_manager.configure()
