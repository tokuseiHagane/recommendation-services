"""
BatchUpsertException: Исключение для ошибок batch upsert VK постов.

Porto Architecture Exception:
- Наследует от Exception
- Используется в BatchUpsertVkPostsTask
"""


class BatchUpsertException(Exception):
    """
    Exception для критических ошибок batch upsert VK постов.
    
    Возникает когда:
    - Не удалось вставить батч в БД
    - Ошибка ON CONFLICT UPDATE
    - Проблемы с подключением к БД
    
    Example:
        >>> try:
        ...     await batch_upsert_vk_posts_task(posts)
        ... except BatchUpsertException as exc:
        ...     logger.error(f"Batch upsert failed: {exc}")
    """
    pass
