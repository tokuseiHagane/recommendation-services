"""
BatchUpsertException: Ошибка batch upsert постов в БД.
"""


class BatchUpsertException(Exception):
    """
    Exception: Ошибка batch upsert постов в БД.
    
    Использование:
    - Raise в BatchUpsertPostsTask при критической ошибке БД
    - Catch в BatchProcessPostsAction для логирования и возможного retry
    """
    pass
