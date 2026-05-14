"""TgPost Services: Singleton сервисы контейнера."""

from .PostObjectsCache import PostObjectsCache
from .DynamicConsumerManager import DynamicConsumerManager

__all__ = [
    "PostObjectsCache",
    "DynamicConsumerManager",
]
