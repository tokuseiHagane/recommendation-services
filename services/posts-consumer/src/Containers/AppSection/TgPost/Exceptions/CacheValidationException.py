"""
CacheValidationException: Ошибка валидации данных для кэша.
"""


class CacheValidationException(Exception):
    """
    Exception: Ошибка валидации данных для кэша.
    
    Использование:
    - Raise в ValidateChannelDataTask при невалидных данных канала
    - Catch в UpdateChannelCacheAction для логирования
    """
    pass
