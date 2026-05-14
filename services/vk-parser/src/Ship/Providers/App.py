"""Application dependency injection provider."""

from dishka import Provider, Scope, provide
from litestar.stores.redis import RedisStore

from src.Containers.AppSection.VkParser.Providers import VkParserProvider
from src.Ship.Configs.App import AppSettings, get_settings
from src.Ship.Core.AuthServiceClient import AuthServiceClient
from src.Ship.Core.Cache import Cache, create_cache_from_store
from src.Ship.Core.JwtVerifier import JwtVerifier
from src.Ship.Core.TokenStorage import TokenStorage, create_token_storage


class AppProvider(Provider):
    """Main application provider."""

    @provide(scope=Scope.APP)
    def provide_settings(self) -> AppSettings:
        return get_settings()

    @provide(scope=Scope.APP)
    def provide_redis_store(self, settings: AppSettings) -> RedisStore:
        return RedisStore.with_client(url=settings.redis_url)

    @provide(scope=Scope.APP)
    def provide_cache(self, redis_store: RedisStore) -> Cache:
        return create_cache_from_store(redis_store)

    @provide(scope=Scope.APP)
    def provide_token_storage(self) -> TokenStorage:
        return create_token_storage()

    @provide(scope=Scope.APP)
    def provide_jwt_verifier(self, settings: AppSettings) -> JwtVerifier:
        return JwtVerifier(settings=settings)

    @provide(scope=Scope.APP)
    def provide_auth_service_client(self, settings: AppSettings) -> AuthServiceClient:
        return AuthServiceClient(settings=settings)


def get_all_providers() -> list[Provider]:
    """Get all application providers."""
    return [
        AppProvider(),
        VkParserProvider(),
    ]
