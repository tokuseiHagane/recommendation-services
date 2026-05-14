"""
CacheValidationException: Исключение для ошибок валидации VK данных.

Porto Architecture Exception:
- Наследует от Exception
- Используется в ValidateGroupDataTask
"""


class CacheValidationException(Exception):
    """
    Exception для ошибок валидации VK данных.
    
    Возникает когда:
    - Невалидные данные VK группы
    - Отсутствуют обязательные поля
    - Неправильные типы данных
    
    Example:
        >>> try:
        ...     await validate_group_data_task(raw_group)
        ... except CacheValidationException as exc:
        ...     logger.warning(f"Validation failed: {exc}")
    """
    pass
