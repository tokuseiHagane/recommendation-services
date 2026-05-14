"""
UpdateChannelCacheAction: Обновление кэша каналов.

Porto Architecture Action:
- Оркестрирует ValidateChannelDataTask → UpdateCacheTask
- Logfire трассировка для observability
- Error handling с CacheValidationException
"""

from typing import Dict, Any
import logging

try:
    import logfire
except ImportError:
    # Fallback если logfire не установлен
    class logfire:  # type: ignore
        @staticmethod
        def span(*args, **kwargs):
            from contextlib import contextmanager
            @contextmanager
            def dummy_span():
                yield
            return dummy_span()
        
        @staticmethod
        def info(*args, **kwargs):
            pass
        
        @staticmethod
        def warning(*args, **kwargs):
            pass

from src.Containers.AppSection.TgPost.Tasks.ValidateChannelDataTask import validate_channel_data_task
from src.Containers.AppSection.TgPost.Tasks.UpdateCacheTask import update_cache_task
from src.Containers.AppSection.TgPost.Exceptions.CacheValidationException import CacheValidationException

logger = logging.getLogger(__name__)


async def update_channel_cache_action(
    channel_data: Dict[str, Any],
    *,
    cache: Any  # PostObjectsCache
) -> bool:
    """
    Action: Обновить кэш каналов из события.
    
    Бизнес use case для обновления кэша при получении событий из tg_channels_diff.
    Оркестрирует:
    1. ValidateChannelDataTask - валидация данных канала
    2. UpdateCacheTask - обновление кэша
    
    Args:
        channel_data: Данные канала из tg_channels_diff
            Expected keys: id, name, type
        cache: PostObjectsCache instance (DI)
    
    Returns:
        True если кэш обновлен, False если данные невалидны
        
    Raises:
        CacheValidationException: Если данные критически невалидны
        
    Example:
        >>> channel_data = {"id": 123, "name": "Tech", "type": "public"}
        >>> success = await update_channel_cache_action(
        ...     channel_data,
        ...     cache=cache
        ... )
        >>> success
        True
    """
    
    channel_id = channel_data.get("id")
    
    with logfire.span(
        "update_channel_cache_action",
        channel_id=channel_id
    ):
        try:
            # 1. Валидация данных канала
            with logfire.span("validate_channel_data"):
                validated_data = await validate_channel_data_task(channel_data)
                
                logger.debug(f"Validated channel data for channel {channel_id}")
            
            # 2. Обновление кэша
            with logfire.span("update_cache"):
                count = await update_cache_task(cache, [validated_data])
                
                logger.info(
                    f"Updated cache with channel {channel_id} (added {count})"
                )
                
                logfire.info(
                    "Cache updated",
                    channel_id=channel_id,
                    added=count
                )
            
            return True
            
        except CacheValidationException as exc:
            logger.error(
                f"Validation failed for channel {channel_id}: {exc}"
            )
            logfire.warning(
                "Channel validation failed",
                channel_id=channel_id,
                error=str(exc)
            )
            # Не raise, возвращаем False для graceful degradation
            return False
        
        except Exception as exc:
            logger.exception(
                f"Unexpected error in update_channel_cache_action "
                f"for channel {channel_id}: {exc}"
            )
            return False

