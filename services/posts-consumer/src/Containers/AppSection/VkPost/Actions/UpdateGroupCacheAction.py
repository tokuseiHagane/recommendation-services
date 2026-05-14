"""
UpdateGroupCacheAction: Обновление кэша VK групп.

Porto Architecture Action:
- Оркестрирует ValidateGroupDataTask + UpdateCacheTask
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

from src.Containers.AppSection.VkPost.Tasks.ValidateGroupDataTask import validate_group_data_task
from src.Containers.AppSection.VkPost.Tasks.UpdateCacheTask import update_cache_task
from src.Containers.AppSection.VkPost.Exceptions.CacheValidationException import CacheValidationException

logger = logging.getLogger(__name__)


async def update_group_cache_action(
    *,
    raw_group: Dict[str, Any],
    cache: Any  # VkGroupsCache
) -> bool:
    """
    Action: Обновить кэш VK групп из события vk_groups_diff.
    
    Бизнес use case для обновления кэша при получении события о группе.
    Оркестрирует:
    1. ValidateGroupDataTask - валидация данных группы
    2. UpdateCacheTask - обновление кэша
    
    Args:
        raw_group: Raw данные VK группы из Kafka
        cache: VkGroupsCache instance (DI)
    
    Returns:
        True если кэш успешно обновлен, False если нет
        
    Example:
        >>> raw_group = {"id": 123, "name": "Tech News", "screen_name": "technews"}
        >>> success = await update_group_cache_action(
        ...     raw_group=raw_group,
        ...     cache=cache
        ... )
        >>> success
        True
    """
    
    group_id = raw_group.get("id", "unknown")
    
    with logfire.span(
        "update_group_cache_action",
        group_id=group_id
    ):
        try:
            # 1. Валидация данных группы
            with logfire.span("validate_group_data"):
                validated_group = await validate_group_data_task(raw_group)
                
                if not validated_group:
                    logger.warning(f"Invalid VK group data for id {group_id}")
                    return False
                
                logger.debug(f"Validated VK group {group_id}")
            
            # 2. Обновление кэша
            with logfire.span("update_cache"):
                count = await update_cache_task(cache, [validated_group])
                
                if count > 0:
                    logger.info(f"Updated cache with VK group {group_id}")
                    logfire.info(
                        "VK Group cache updated",
                        group_id=group_id
                    )
                    return True
                else:
                    logger.warning(f"Failed to update cache for VK group {group_id}")
                    return False
            
        except CacheValidationException as exc:
            logger.warning(f"VK Group validation failed for {group_id}: {exc}")
            logfire.warning(
                "VK Group validation failed",
                group_id=group_id,
                error=str(exc)
            )
            return False
        
        except Exception as exc:
            logger.exception(
                f"Unexpected error updating VK group cache for {group_id}: {exc}"
            )
            return False
