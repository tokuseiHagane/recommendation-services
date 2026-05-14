"""Logfire plugin for Litestar."""

from __future__ import annotations

import logfire
from litestar.config.app import AppConfig
from litestar.plugins import InitPlugin

from src.Ship.Configs.App import get_settings


class LogfirePlugin(InitPlugin):
    """Logfire integration plugin for Litestar."""

    def __init__(self, auto_trace_modules: list[str] | None = None, min_duration: float = 0.01):
        """Initialize Logfire plugin.

        Args:
            auto_trace_modules: Modules to auto-trace
            min_duration: Minimum duration for auto-tracing (in seconds)
        """
        self.auto_trace_modules = auto_trace_modules or []
        self.min_duration = min_duration
        self._configured = False
        super().__init__()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Configure Logfire on app initialization.

        Args:
            app_config: Application configuration

        Returns:
            Updated application configuration
        """
        if not self._configured:
            self._setup_logfire()
            self._configured = True

        app_config.on_startup.append(self._instrument_app)

        return app_config

    def _setup_logfire(self) -> None:
        """Setup Logfire configuration."""
        settings = get_settings()
        min_log_level = settings.logfire_log_level.lower()

        if settings.logfire_token:
            logfire.configure(
                service_name=settings.app_name,
                token=settings.logfire_token,
                send_to_logfire=True,
                project_name=settings.logfire_project_name,
                environment=settings.app_env,
                inspect_arguments=True,
                console=logfire.ConsoleOptions(
                    verbose=settings.app_debug,
                    include_timestamps=True,
                    min_log_level=min_log_level,
                    colors="auto",
                ),
            )
        else:
            logfire.configure(
                send_to_logfire=False,
                service_name=settings.app_name,
                console=logfire.ConsoleOptions(
                    verbose=settings.app_debug,
                    include_timestamps=True,
                    min_log_level=min_log_level,
                    colors="auto",
                ),
            )

        if self.auto_trace_modules:
            logfire.install_auto_tracing(
                modules=self.auto_trace_modules,
                min_duration=self.min_duration,
                check_imported_modules="ignore",
            )

        logfire.info("Logfire configured successfully", environment=settings.app_env)

    async def _instrument_app(self) -> None:
        """Instrument application components."""
        try:
            logfire.instrument_httpx()
            logfire.info("Application instrumentation completed")
        except Exception as e:
            logfire.error("Failed to instrument application", error=str(e))
