"""PostgreSQL database configuration with Piccolo ORM."""

from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

from src.Ship.Configs.App import get_settings


def get_engine() -> PostgresEngine:
    """Get PostgreSQL database engine configured via Piccolo."""
    settings = get_settings()

    url = settings.database_url
    if not (url.startswith("postgresql://") or url.startswith("postgres://")):
        raise ValueError(f"Only PostgreSQL databases are supported. Got: {url}")

    # Parse URL and create config dict for Piccolo
    import urllib.parse

    parsed = urllib.parse.urlparse(url)

    config = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": parsed.username,
        "password": parsed.password,
        "database": parsed.path.lstrip("/") if parsed.path else "postgres",
    }

    return PostgresEngine(config=config)


# Database engine instance (Piccolo)
DB = get_engine()

# App registry for Piccolo
APP_REGISTRY = AppRegistry(
    apps=[
        "src.Containers.AppSection.VkParser.PiccoloApp",
    ]
)
