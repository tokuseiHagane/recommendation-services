"""
BatchProcessPostsAction: Обработка батча постов из Kafka топика.

Porto Architecture Action:
- Оркестрирует ValidatePostsTask + BatchUpsertPostsTask
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

from src.Containers.AppSection.TgPost.Tasks.ValidatePostsTask import validate_posts_task
from src.Containers.AppSection.TgPost.Tasks.BatchUpsertPostsTask import batch_upsert_posts_task
from src.Containers.AppSection.TgPost.Exceptions.BatchUpsertException import BatchUpsertException

logger = logging.getLogger(__name__)


async def batch_process_posts_action(
    raw_posts: List[Dict[str, Any]],
    *,
    channel_id: int,
    metadata_list: Optional[List[Dict[str, Any]]] = None
) -> int:
    """
    Action: Обработать батч постов из Kafka топика.
    
    Бизнес use case для обработки батча постов с валидацией и сохранением в БД.
    Оркестрирует:
    1. ValidatePostsTask - валидация структуры
    2. BatchUpsertPostsTask - batch insert с ON CONFLICT UPDATE
    
    Args:
        raw_posts: Список raw постов из Kafka
        channel_id: ID канала для логирования
        metadata_list: Опциональные метаданные (topic, partition, offset)
    
    Returns:
        Количество успешно сохраненных постов
        
    Raises:
        BatchUpsertException: Если batch upsert полностью провалился
        
    Example:
        >>> raw_posts = [
        ...     {"id": 123, "content": "Post 1", "id_channels": 456},
        ...     {"id": 124, "content": "Post 2", "id_channels": 456}
        ... ]
        >>> count = await batch_process_posts_action(
        ...     raw_posts,
        ...     channel_id=456
        ... )
        >>> count
        2
    """
    
    with logfire.span(
        "batch_process_posts_action",
        channel_id=channel_id,
        batch_size=len(raw_posts)
    ):
        try:
            # 1. Валидация постов
            with logfire.span("validate_posts"):
                validated_posts = await validate_posts_task(raw_posts)
                
                logger.info(
                    f"Validated {len(validated_posts)}/{len(raw_posts)} posts "
                    f"for channel {channel_id}"
                )
                
                logfire.info(
                    "Posts validated",
                    channel_id=channel_id,
                    validated=len(validated_posts),
                    total=len(raw_posts)
                )
            
            if not validated_posts:
                logger.warning(
                    f"No valid posts to insert for channel {channel_id}"
                )
                return 0
            
            # 2. Batch upsert в БД
            with logfire.span("batch_upsert_posts"):
                inserted_count = await batch_upsert_posts_task(validated_posts)
                
                logger.info(
                    f"Inserted {inserted_count} posts for channel {channel_id}"
                )
                
                logfire.info(
                    "Posts upserted",
                    channel_id=channel_id,
                    inserted=inserted_count
                )
            
            # Метрика для мониторинга (как атрибут логирования)
            logfire.info(
                "Batch processing completed",
                posts_processed=inserted_count,
                channel_id=channel_id
            )
            
            return inserted_count
            
        except BatchUpsertException as exc:
            logger.exception(
                f"Batch upsert failed for channel {channel_id}: {exc}"
            )
            logfire.info(
                "Batch upsert failed",
                channel_id=channel_id,
                error=str(exc)
            )
            raise
        
        except Exception as exc:
            logger.exception(
                f"Unexpected error in batch_process_posts_action "
                f"for channel {channel_id}: {exc}"
            )
            # Не raise, чтобы продолжить обработку других сообщений
            return 0

