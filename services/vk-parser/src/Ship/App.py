"""Main Litestar application factory."""

from dishka import make_async_container
from dishka.integrations.litestar import setup_dishka
from litestar import Litestar, Router
from litestar.config.cors import CORSConfig
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.routes import HTTPRoute, WebSocketRoute
from litestar.stores.redis import RedisStore

from src.Containers.AppSection.VkParser.UI.API.Controllers.VkParserController import (
    VkHealthController,
    VkParserController,
    VkSearchController,
)
from src.Containers.AppSection.VkParser.UI.API.Controllers.VkReadController import (
    VkGroupsController,
    VkPostsController,
)
from src.Containers.AppSection.VkParser.UI.API.Controllers.VkSearchWsController import vk_search_ws
from src.Ship.Configs.App import get_settings
from src.Ship.Exceptions.Handlers import exception_handler
from src.Ship.Parents.Exception import PortoException
from src.Ship.Plugins.LogfirePlugin import LogfirePlugin
from src.Ship.Providers.App import get_all_providers


def print_routes(app: Litestar) -> None:
    """Print all registered routes in a formatted table."""
    print("\n" + "=" * 80)
    print("REGISTERED ROUTES")
    print("=" * 80)

    routes_info = []
    for route in app.routes:
        if isinstance(route, HTTPRoute):
            for handler in route.route_handlers:
                methods = getattr(handler, "http_methods", set())
                methods_str = ", ".join(sorted(methods)) if methods else "N/A"
                path = route.path
                handler_name = getattr(handler, "handler_name", None) or getattr(handler.fn, "__name__", "unknown")
                routes_info.append((path, methods_str, handler_name))
        elif isinstance(route, WebSocketRoute):
            path = route.path
            handler = route.route_handler
            handler_name = getattr(handler, "handler_name", None) or getattr(handler.fn, "__name__", "unknown")
            routes_info.append((path, "WS", handler_name))

    routes_info.sort(key=lambda x: x[0])

    print(f"{'Path':<50} {'Methods':<15} {'Handler'}")
    print("-" * 80)

    for path, methods, handler_name in routes_info:
        print(f"{path:<50} {methods:<15} {handler_name}")

    print("=" * 80)
    print(f"Total routes: {len(routes_info)}\n")


def create_app() -> Litestar:
    """Create and configure Litestar application."""

    settings = get_settings()

    container = make_async_container(*get_all_providers())

    redis_store = RedisStore.with_client(url=settings.redis_url)

    # Rate-limiting (§3 design plan). In-memory, per-replica — Litestar's
    # StoreRegistry auto-creates a MemoryStore for each unique ``store`` name.
    # We stack three middlewares:
    #   - global (60 rpm) for every HTTP call except docs/health
    #   - stricter for POST /parse/vk (heavy synchronous parse)
    #   - stricter for GET /search/vk
    docs_path = f"/api/{settings.api_version}/{settings.service_name}/docs"
    health_path = f"/api/{settings.api_version}/health"
    parse_path = f"/api/{settings.api_version}/parse/vk"
    search_path = f"/api/{settings.api_version}/search/vk"

    def _only_path(target_path: str):
        async def _check(request) -> bool:  # noqa: ANN001
            return request.url.path == target_path

        return _check

    global_rate_limit = RateLimitConfig(
        rate_limit=("minute", settings.rate_limit_global_per_minute),
        exclude=[docs_path, health_path],
        store="rate_limit_global",
    )
    parse_rate_limit = RateLimitConfig(
        rate_limit=("minute", settings.rate_limit_parse_per_minute),
        check_throttle_handler=_only_path(parse_path),
        store="rate_limit_parse",
    )
    search_rate_limit = RateLimitConfig(
        rate_limit=("minute", settings.rate_limit_search_per_minute),
        check_throttle_handler=_only_path(search_path),
        store="rate_limit_search",
    )

    api_router = Router(
        path=f"/api/{settings.api_version}",
        route_handlers=[
            VkParserController,
            VkSearchController,
            VkHealthController,
            VkGroupsController,
            VkPostsController,
            vk_search_ws,
        ],
    )

    app = Litestar(
        route_handlers=[
            api_router,
        ],
        exception_handlers={
            PortoException: exception_handler,
        },
        middleware=[
            global_rate_limit.middleware,
            parse_rate_limit.middleware,
            search_rate_limit.middleware,
        ],
        cors_config=CORSConfig(
            allow_origins=settings.cors_allow_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        ),
        openapi_config=OpenAPIConfig(
            title=settings.app_name,
            version=settings.api_version,
            path=f"/api/{settings.api_version}/{settings.service_name}/docs",
            render_plugins=[ScalarRenderPlugin()],
        ),
        stores={
            "redis": redis_store,
        },
        plugins=[
            LogfirePlugin(
                auto_trace_modules=["src.Containers"],
                min_duration=0.05,
            ),
        ],
        debug=settings.app_debug,
        logging_config=None,
    )

    setup_dishka(container, app)

    print_routes(app)

    return app
