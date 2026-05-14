"""
BatchProcessVkPostsAction: Обработка батча VK постов из Kafka топика.

Porto Architecture Action:
- Оркестрирует ValidateVkPostsTask + BatchUpsertVkPostsTask
- Logfire трассировка для observability
- Error handling с BatchUpsertException
"""

from typing import Dict, Any, List, Optional
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
        def metric(*args, **kwargs):
            pass

from src.Containers.AppSection.VkPost.Tasks.ValidateVkPostsTask import validate_vk_posts_task
from src.Containers.AppSection.VkPost.Tasks.BatchUpsertVkPostsTask import batch_upsert_vk_posts_task
from src.Containers.AppSection.VkPost.Exceptions.BatchUpsertException import BatchUpsertException

logger = logging.getLogger(__name__)


async def batch_process_vk_posts_action(
    raw_posts: List[Dict[str, Any]],
    *,
    group_id: int,
    metadata_list: Optional[List[Dict[str, Any]]] = None
) -> int:
    """
    Action: Обработать батч VK постов из Kafka топика.
    
    Бизнес use case для обработки батча VK постов с валидацией и сохранением в БД.
    Оркестрирует:
    1. ValidateVkPostsTask - валидация структуры
    2. BatchUpsertVkPostsTask - batch insert с ON CONFLICT UPDATE
    
    Args:
        raw_posts: Список raw VK постов из Kafka
        group_id: ID VK группы для логирования
        metadata_list: Опциональные метаданные (topic, partition, offset)
    
    Returns:
        Количество успешно сохраненных постов
        
    Raises:
        BatchUpsertException: Если batch upsert полностью провалился
        
    Example:
        >>> raw_posts = [
        ...     {"id": 123, "len_message": 100, "id_groups": 456},
        ...     {"id": 124, "len_message": 200, "id_groups": 456}
        ... ]
        >>> count = await batch_process_vk_posts_action(
        ...     raw_posts,
        ...     group_id=456
        ... )
        >>> count
        2
    """
    
    with logfire.span(
        "batch_process_vk_posts_action",
        group_id=group_id,
        batch_size=len(raw_posts)
    ):
        try:
            # 1. Валидация постов
            with logfire.span("validate_vk_posts"):
                validated_posts = await validate_vk_posts_task(raw_posts)
                
                logger.info(
                    f"Validated {len(validated_posts)}/{len(raw_posts)} VK posts "
                    f"for group {group_id}"
                )
                
                logfire.info(
                    "VK Posts validated",
                    group_id=group_id,
                    validated=len(validated_posts),
                    total=len(raw_posts)
                )
            
            if not validated_posts:
                logger.warning(
                    f"No valid VK posts to insert for group {group_id}"
                )
                return 0
            
            # 2. Batch upsert в БД
            with logfire.span("batch_upsert_vk_posts"):
                inserted_count = await batch_upsert_vk_posts_task(validated_posts)
                
                logger.info(
                    f"Inserted {inserted_count} VK posts for group {group_id}"
                )
                
                logfire.info(
                    "VK Posts upserted",
                    group_id=group_id,
                    inserted=inserted_count
                )
            
            # Метрика для мониторинга
            logfire.info(
                "VK Batch processing completed",
                posts_processed=inserted_count,
                group_id=group_id
            )
            
            return inserted_count
            
        except BatchUpsertException as exc:
            logger.exception(
                f"VK Batch upsert failed for group {group_id}: {exc}"
            )
            logfire.info(
                "VK Batch upsert failed",
                group_id=group_id,
                error=str(exc)
            )
            raise
        
        except Exception as exc:
            logger.exception(
                f"Unexpected error in batch_process_vk_posts_action "
                f"for group {group_id}: {exc}"
            )
            # Не raise, чтобы продолжить обработку других сообщений
            return 0
