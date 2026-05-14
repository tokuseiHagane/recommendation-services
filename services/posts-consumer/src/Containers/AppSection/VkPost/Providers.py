"""
VkPost Dishka Providers: DI конфигурация для контейнера.

Porto Architecture DI:
- Services: APP scope (singletons)
- Actions: REQUEST scope (created on demand)
- Config: APP scope
"""

from dishka import Provider, Scope, provide

from src.Containers.AppSection.VkPost.Config.container_settings import (
    container_settings,
    VkPostContainerSettings
)
from src.Containers.AppSection.VkPost.Services.VkGroupsCache import VkGroupsCache
from src.Containers.AppSection.VkPost.Services.VkDynamicConsumerManager import VkDynamicConsumerManager


class VkPostProvider(Provider):
    """
    Dishka Provider для VkPost контейнера.
    
    Регистрирует:
    - Config (APP scope)
    - Services (APP scope - singletons)
    - Actions можно регистрировать по необходимости
    """
    
    @provide(scope=Scope.APP)
    def container_settings(self) -> VkPostContainerSettings:
        """Singleton конфигурация контейнера."""
        return container_settings
    
    @provide(scope=Scope.APP)
    def vk_groups_cache(
        self,
        settings: VkPostContainerSettings
    ) -> VkGroupsCache:
        """Singleton кэш VK групп."""
        return VkGroupsCache(
            ttl_seconds=settings.cache_ttl_seconds
        )
    
    @provide(scope=Scope.APP)
    def vk_dynamic_consumer_manager(
        self,
        settings: VkPostContainerSettings,
        cache: VkGroupsCache
    ) -> VkDynamicConsumerManager:
        """Singleton менеджер VK консьюмеров."""
        return VkDynamicConsumerManager(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            cache=cache
        )
