from __future__ import annotations

from src.VkParser.models import VkMethodsWall
from src.VkParser.vk_raw_types import VkWallPostRaw


async def fetch_wall_post_date_at_offset(
    pool_factory,
    domain: str,
    offset: int,
) -> int | None:
    """
    Делает запрос wall.get(count=1, offset=offset) и возвращает timestamp поста.
    Возвращает None, если items пустые или результат неожиданной формы.

    pool_factory: callable, который возвращает async context manager пула:
      async with pool_factory() as pool:
          ...
    """
    method_arg_pairs = [
        (
            VkMethodsWall.GET.value,
            {"domain": domain, "count": 1, "offset": offset},
            {"domain": domain, "offset": offset},
        )
    ]

    async with pool_factory() as pool:
        parsed_results, _errors = await pool.add_calls_with_results(posts=method_arg_pairs)

    # ожидаем: parsed_results["posts"] = [(result_dict, meta)]
    posts_list = parsed_results.get("posts", [])
    if not posts_list:
        return None

    result_dict, _meta = posts_list[0]
    items: list[VkWallPostRaw] = result_dict.get("items", [])  # type: ignore[assignment]
    if not items:
        return None

    # берём дату последнего элемента
    return items[-1].get("date")
