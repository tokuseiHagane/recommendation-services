from __future__ import annotations


def normalize_wall_range(start_index: int, end_index: int) -> tuple[int, int]:
    """
    Нормализует порядок индексов, чтобы получить корректный диапазон для обхода.
    В текущей логике парсера ожидаем, что end_index <= start_index.
    """
    if end_index > start_index:
        end_index, start_index = start_index, end_index
    return start_index, end_index


def build_wall_offsets(start_index: int, end_index: int, step: int = 100) -> list[int]:
    """
    Строит offsets для wall.get.
    Важно: offset в VK wall.get — смещение от самых новых постов (0 = самый новый пост).
    Мы обходим все страницы от end_index до start_index с шагом step.
    """
    return list(range(end_index, start_index + 1, step))
