"""Bootstrap file for VK Parser Service with enhanced Logfire logging.

This file configures environment-specific Logfire logging BEFORE importing
any application modules to ensure proper tracing and observability.
"""

import logfire
import uvicorn

# Configure Logfire BEFORE importing application modules
from src.Ship.Core.Logging import configure_logging, get_service_logger

# Initialize logging system
configure_logging()

# Get service logger
service_logger = get_service_logger(__name__)

# Log service startup
logfire.info("🚀 Starting VK Parser Service", service="vk-parser-service", version="0.1.0", component="bootstrap")

def run_server() -> None:
    """Run the VK Parser Service server."""
    try:
        # Import after logging setup so startup instrumentation is configured first.
        from src.Ship.App import create_app

        # Create app
        logfire.info("🏗️ Creating VK Parser Service application")
        app = create_app()

        # Get settings
        from src.Ship.Configs.App import get_settings

        settings = get_settings()

        # Log startup configuration
        logfire.info(
            "🌐 Starting VK Parser Service server",
            host=settings.app_host,
            port=settings.app_port,
            environment=settings.app_env,
            debug_mode=settings.app_debug,
            redis_url=settings.redis_url,
        )

        # Run server
        uvicorn.run(
            app,
            host=settings.app_host,
            port=settings.app_port,
            reload=False,
            log_level="debug" if settings.app_debug else "info",
        )

    except Exception as e:
        logfire.error(
            "💥 Failed to start VK Parser Service", error=str(e), error_type=type(e).__name__, component="bootstrap"
        )
        raise


if __name__ == "__main__":
    run_server()
