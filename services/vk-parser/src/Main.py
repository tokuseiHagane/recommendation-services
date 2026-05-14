"""Application entry point."""

import uvicorn

from src.Ship.App import create_app
from src.Ship.Configs.App import get_settings


def run_server() -> None:
    """Run the application server."""
    settings = get_settings()

    if settings.is_development:
        # Use string import for reload in development
        uvicorn.run(
            "src.Main:create_app_instance",
            host=settings.app_host,
            port=settings.app_port,
            reload=True,
            log_level="debug" if settings.app_debug else "info",
            factory=True,
        )
    else:
        # Use app object in production
        app = create_app()
        uvicorn.run(
            app,
            host=settings.app_host,
            port=settings.app_port,
            reload=False,
            log_level="debug" if settings.app_debug else "info",
        )


def create_app_instance():
    """Create app instance for uvicorn with string import."""
    return create_app()


if __name__ == "__main__":
    run_server()
