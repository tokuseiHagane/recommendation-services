from __future__ import annotations

import datetime as dt

import anyio
from aiovk import API, TokenSession
from aiovk.exceptions import VkAPIError
from aiovk.pools import chunks

from src.VkParser.execute_pool import AdvancedExecutePool
from src.VkParser.group_state import group_state
from src.VkParser.logging_utils import get_logger
from src.VkParser.models import VkMethodsGroups, VkMethodsUsers, VkMethodsWall
from src.VkParser.post_processing import (
    collect_wall_posts,
    dedupe_posts_by_owner_and_id,
    filter_posts_by_date,
)
from src.VkParser.vk_raw_types import VkGroupInfoRaw, VkUserInfoRaw
from src.VkParser.wall_fetch import fetch_wall_post_date_at_offset
from src.VkParser.wall_offsets import build_wall_offsets, normalize_wall_range

logger = get_logger(__name__)


group_request_params: str = ",".join(
    [
        "activity",
        "age_limits",
        "counters",
        "description",
        "status",
        "members_count",
        "ban_info",
        "deactivated",
        "is_closed",
        "photo_200",
        "cover",
    ]
)


class CustomTokenSession(TokenSession):
    async def send_api_request(
        self, method_name: str, method_args: dict = None, timeout: int = None, raw_response: bool = False
    ):
        while True:
            try:
                return await super().send_api_request(method_name, method_args, timeout, raw_response)
            except VkAPIError as e:
                if e.error_code == 6:  # Too many requests per second
                    sleep_time = 3
                    await anyio.sleep(sleep_time)  # Add a delay before retrying
                else:
                    # print(f"Неизвестная ошибка {e}")
                    raise e


class VkParser:
    """
    Клиент для работы с VK API.

    Инкапсулирует:
        - сессию VK
        - execute-пулы
        - алгоритмы бинарного поиска по дате
        - получение постов и метаданных групп
    """

    def __init__(self, token: str):
        self.token: str = token
        self.session: CustomTokenSession = CustomTokenSession(access_token=token, timeout=30)
        self.api: API = API(self.session)

    async def search(self, q: str) -> dict:
        """
        Выполняет глобальный поиск через VK API (search.getHints).

        :param q: строка запроса
        :return: сырой ответ VK API
        """
        return await self.api.search.getHints(q=q, search_global=1, fields="screen_name,photo_50,photo_100,photo_200")

    async def get_posts_count(self, infos: dict[str, group_state]) -> None:
        """
        Для каждой группы получает общее количество постов
        и записывает значение в поле posts_count модели group_state.
        """
        method_arg_pairs = [
            (VkMethodsWall.GET.value, {"domain": domain, "count": 1}, {"domain": domain}) for domain in infos
        ]

        async with AdvancedExecutePool(self.api) as pool:
            parsed_results, errors = await pool.add_calls_with_results(posts_count=method_arg_pairs)

        for result, meta in parsed_results["posts_count"]:
            domain = meta["domain"]
            infos[domain].posts_count = result.get("count", 0) or 0

        for error, meta in errors["posts_count"]:
            domain = meta["domain"]
            logger.warning(
                "failed to fetch posts count for domain=%s error=%s",
                domain,
                error,
            )
            infos[domain].posts_count = 0

    async def binary_search_date(
        self, domain: str, target_date: dt.datetime, total_posts: int, is_start_date=True
    ) -> int:
        """
        Выполняет бинарный поиск по offset для нахождения индекса поста,
        соответствующего заданной дате.

        :param domain: screen_name группы
        :param target_date: дата для поиска
        :param total_posts: общее количество постов в группе
        :param is_start_date: режим поиска начала диапазона (True) или конца (False)
        :return: найденный индекс offset
        """
        left, right = 0, total_posts - 1
        target_timestamp = target_date.timestamp()

        def pool_factory():
            return AdvancedExecutePool(self.api, call_number_per_request=12)

        while left <= right:
            mid = (left + right) // 2
            offset = mid

            if offset >= total_posts:
                return mid

            mid_date = await fetch_wall_post_date_at_offset(pool_factory, domain, offset)

            if mid_date is None:
                if is_start_date:
                    right = mid - 1
                else:
                    left = mid + 1
                continue

            if is_start_date:
                if mid_date < target_timestamp:
                    right = mid - 1
                else:
                    left = mid + 1
            else:
                if mid_date > target_timestamp:
                    left = mid + 1
                else:
                    right = mid - 1

            if mid_date == target_timestamp:
                return mid

        return left if left < total_posts else right

    async def get_wall_posts(
        self,
        infos: dict[str, group_state],
        start_date: dt.datetime,
        end_date: dt.datetime,
    ) -> None:
        """
        Загружает посты для каждой группы в диапазоне дат
        и записывает их в поле posts модели group_state.

        Включает:
        - бинарный поиск границ
        - построение offsets
        - загрузку страниц wall.get
        - фильтрацию и дедупликацию постов
        """
        start_ts = start_date.timestamp()
        end_ts = end_date.timestamp()

        for domain, info in infos.items():
            total_posts = info.posts_count or 0
            if total_posts <= 0:
                info.posts = []
                continue

            start_index = await self.binary_search_date(domain, start_date, total_posts, is_start_date=True)
            end_index = await self.binary_search_date(domain, end_date, total_posts, is_start_date=False)

            start_index, end_index = normalize_wall_range(start_index, end_index)
            offsets = build_wall_offsets(start_index, end_index, step=100)

            method_arg_pairs = [
                (
                    VkMethodsWall.GET.value,
                    {"domain": domain, "count": 100, "offset": offset},
                    {"domain": domain, "offset": offset},
                )
                for offset in offsets
            ]

            async with AdvancedExecutePool(self.api, call_number_per_request=12) as pool:
                parsed_results, _errors = await pool.add_calls_with_results(posts=method_arg_pairs)

            raw_posts = collect_wall_posts(parsed_results)
            filtered_posts = filter_posts_by_date(raw_posts, start_ts, end_ts)
            unique_posts = dedupe_posts_by_owner_and_id(filtered_posts)

            info.posts = unique_posts

    async def get_counters_users(self, users_info: dict[str, VkUserInfoRaw]) -> None:
        user_method_arg_pairs = [
            (VkMethodsUsers.GET.value, {"user_ids": user_id, "fields": "counters"}, {"domain": user_id})
            for user_id in users_info
        ]

        async with AdvancedExecutePool(self.api) as pool:
            parsed_results, errors = await pool.add_calls_with_results(users=user_method_arg_pairs)

            if errors["users"]:
                logger.warning("errors fetching user counters: %s", errors["users"])

        for result, meta in parsed_results["users"]:
            domain = meta["domain"]
            users_info[domain]["counters"] = result[0].get("counters")

    async def get_wall_info(
        self,
        user_domains: list[str],
        group_domains: list[str],
    ) -> tuple[dict[str, VkUserInfoRaw], dict[str, VkGroupInfoRaw]]:
        user_chunks = chunks(user_domains, 1000)
        group_chunks = chunks(group_domains, 500)

        user_method_arg_pairs = [
            (
                VkMethodsUsers.GET.value,
                {
                    "user_ids": ",".join(chunk),
                    "fields": "deactivated,ban_info,followers_count,photo_200,domain,is_closed",
                },
            )
            for chunk in user_chunks
        ]

        group_method_arg_pairs = [
            (VkMethodsGroups.GET_BY_ID.value, {"group_ids": ",".join(chunk), "fields": group_request_params})
            for chunk in group_chunks
        ]

        async with AdvancedExecutePool(self.api) as pool:
            parsed_results, _errors = await pool.add_calls_with_results(
                users=user_method_arg_pairs,
                groups=group_method_arg_pairs,
            )

        users_info = {info["domain"]: info for info_list in parsed_results["users"] for info in info_list}
        groups_info = {info["screen_name"]: info for info_list in parsed_results["groups"] for info in info_list}

        return users_info, groups_info

    async def resolve_domain_links(self, urls: list[str]) -> tuple[list[str], list[str], list]:
        domains = [url.split("/")[-1] for url in urls]
        method_arg_pairs = [
            ("utils.resolveScreenName", {"screen_name": domain}, {"domain": domain}) for domain in domains
        ]

        async with AdvancedExecutePool(self.api) as pool:
            parsed_results, errors = await pool.add_calls_with_results(resolve=method_arg_pairs)

        users, groups = [], []

        for result, meta in parsed_results["resolve"]:
            domain = meta["domain"]

            if result:
                match result["type"]:
                    case "user":
                        users.append(domain)
                    case "group" | "page":
                        groups.append(domain)
                    case _:  # Unknown type
                        ...
                        # print(f"Неизвестный тип {result['type']} у {domain}")

        return users, groups, errors

    async def close(self) -> None:
        await self.session.close()
