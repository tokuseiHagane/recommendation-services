"""
TgPost Dishka Providers: DI конфигурация для контейнера.

Porto Architecture DI:
- Services: APP scope (singletons)
- Actions: REQUEST scope (created on demand)
- Config: APP scope
"""

from dishka import Provider, Scope, provide
from typing import Any

from src.Containers.AppSection.TgPost.Config.container_settings import (
    container_settings,
    TgPostContainerSettings
)
from src.Containers.AppSection.TgPost.Services.PostObjectsCache import PostObjectsCache
from src.Containers.AppSection.TgPost.Services.DynamicConsumerManager import DynamicConsumerManager


class TgPostProvider(Provider):
    """
    Dishka Provider для TgPost контейнера.
    
    Регистрирует:
    - Config (APP scope)
    - Services (APP scope - singletons)
    - Actions можно регистрировать по необходимости
    """
    
    @provide(scope=Scope.APP)
    def container_settings(self) -> TgPostContainerSettings:
        """Singleton конфигурация контейнера."""
        return container_settings
    
    @provide(scope=Scope.APP)
    def post_objects_cache(
        self,
        settings: TgPostContainerSettings
    ) -> PostObjectsCache:
        """Singleton кэш каналов."""
        return PostObjectsCache(
            ttl_seconds=settings.cache_ttl_seconds
        )
    
    @provide(scope=Scope.APP)
    def dynamic_consumer_manager(
        self,
        settings: TgPostContainerSettings,
        cache: PostObjectsCache
    ) -> DynamicConsumerManager:
        """Singleton менеджер консьюмеров."""
        return DynamicConsumerManager(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            cache=cache
        )

