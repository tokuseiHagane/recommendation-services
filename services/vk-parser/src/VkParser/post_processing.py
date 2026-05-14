from __future__ import annotations

from typing import Any

from src.VkParser.vk_raw_types import VkWallPostRaw


def collect_wall_posts(parsed_results: dict[str, Any]) -> list[VkWallPostRaw]:
    """
    Собирает все items из parsed_results['posts'] в один список.
    Ожидаемая структура: parsed_results['posts'] = [(result_dict, meta), ...]
    """
    raw_posts: list[VkWallPostRaw] = []

    for result, _meta in parsed_results.get("posts", []):
        items = result.get("items", [])
        raw_posts.extend(items)

    return raw_posts


def filter_posts_by_date(
    posts: list[VkWallPostRaw],
    start_ts: float,
    end_ts: float,
) -> list[VkWallPostRaw]:
    """
    Фильтрация постов по timestamp (post['date']).
    """
    return [p for p in posts if start_ts <= p.get("date", 0) <= end_ts]


def dedupe_posts_by_owner_and_id(posts: list[VkWallPostRaw]) -> list[VkWallPostRaw]:
    """
    Уникализация по (owner_id, id) — безопаснее, чем только id.
    Сохраняет порядок (первое вхождение выигрывает).
    """
    seen: set[tuple[int | None, int | None]] = set()
    unique_posts: list[VkWallPostRaw] = []

    for p in posts:
        key = (p.get("owner_id"), p.get("id"))
        if key in seen:
            continue
        seen.add(key)
        unique_posts.append(p)

    return unique_posts
