from __future__ import annotations

import datetime as dt
import gc
from typing import Any

from src.VkParser.extractors import extract_group_row, extract_post_row
from src.VkParser.group_state import group_state
from src.VkParser.logging_utils import get_logger
from src.VkParser.models import GroupRow, PostRow
from src.VkParser.sorting import default_sort_params, sort_posts
from src.VkParser.vk_client import VkParser

logger = get_logger(__name__)


async def search_vk(token: str, q: str) -> dict[str, Any]:
    parser = VkParser(token)
    try:
        return await parser.search(q)
    finally:
        await parser.close()
        gc.collect()


async def get_vk_data(
    token: str,
    links: list[str],
    start_date: dt.datetime,
    end_date: dt.datetime,
    top_n: int = 10,
    sort_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the parser payload used by the Porto VkParser runtime path.
    """
    parser = VkParser(token)
    try:
        _users, groups, _errors = await parser.resolve_domain_links(links)
        logger.info("resolved links: groups=%s errors=%s", groups, _errors)
        if not groups:
            return {}

        _users_info, raw_groups_info = await parser.get_wall_info([], groups)

        groups_info: dict[str, group_state] = {
            key: group_state.model_validate(value) for key, value in raw_groups_info.items()
        }

        logger.info("got wall info: groups=%d", len(groups_info))

        await parser.get_posts_count(groups_info)
        logger.info(
            "got posts count. Groups info after count: %s", [(k, v.posts_count) for k, v in groups_info.items()]
        )
        await parser.get_wall_posts(groups_info, start_date, end_date)
        logger.info("got wall posts. Groups info after posts: %s", [(k, len(v.posts)) for k, v in groups_info.items()])

        effective_sort_params = sort_params or default_sort_params()
        result: dict[str, Any] = {}

        for domain, info in groups_info.items():
            group_row = extract_group_row(info.model_dump())
            post_rows = [extract_post_row(post) for post in info.posts]
            result[group_row.screen_name or domain] = _build_domain_response(
                group=group_row,
                posts=post_rows,
                top_n=top_n,
                sort_params=effective_sort_params,
            )

        return result

    finally:
        await parser.close()
        gc.collect()


def _build_domain_response(
    *,
    group: GroupRow,
    posts: list[PostRow],
    top_n: int,
    sort_params: dict[str, Any],
) -> dict[str, Any]:
    graph_posts = [_build_graph_post(post) for post in posts]
    sorted_posts = _sort_graph_posts(graph_posts, sort_params=sort_params)
    members_count = group.members_count
    return {
        "id": group.id,
        "name": group.name,
        "screen_name": group.screen_name,
        "members_count": members_count,
        "posts_count": len(sorted_posts),
        "top_posts": [post.copy() for post in sorted_posts[:top_n]],
        "down_posts": [post.copy() for post in reversed(sorted_posts[-top_n:])] if sorted_posts else [],
        "graph_data": [_strip_graph_post_id(post) for post in sorted_posts],
        "period_posts_metrics": _build_period_posts_metrics(sorted_posts, members_count),
        # Internal channel for ParseVkDataAction._flatten_parsed_result: raw PostRow
        # dumps in flat schema, persisted to PostgreSQL and fanned out to Kafka.
        # Must stay in Python mode — SaveParsedDataTask upserts VkPost through
        # Piccolo, and asyncpg rejects ISO strings for timestamptz columns with
        # ``DataError: expected a datetime.date or datetime.datetime instance``.
        # PublishToKafkaTask re-dumps via KafkaPostMessage.model_dump(mode="json"),
        # so Kafka still receives proper ISO timestamps.
        "posts": [post.model_dump() for post in posts],
    }


def _build_graph_post(post: PostRow) -> dict[str, Any]:
    return {
        "id": post.id,
        "date": _serialize_datetime(post.message_timestamp),
        "edit_date": _serialize_datetime(post.edit_date),
        "views": post.view_count,
        "likes": post.reactions_count,
        "comments": post.comments_count,
        "reposts": post.repost_count,
        "text_len": post.len_message,
    }


def _sort_graph_posts(posts: list[dict[str, Any]], *, sort_params: dict[str, Any]) -> list[dict[str, Any]]:
    sortable_posts = [
        {
            "id": index,
            "date": _to_timestamp(post.get("date")),
            "views": {"count": post.get("views", 0)},
            "likes": {"count": post.get("likes", 0)},
            "comments": {"count": post.get("comments", 0)},
            "reposts": {"count": post.get("reposts", 0)},
        }
        for index, post in enumerate(posts)
    ]
    sorted_posts = sort_posts(sortable_posts, sort_params)
    posts_by_index = dict(enumerate(posts))
    return [posts_by_index[item["id"]].copy() for item in sorted_posts]


def _strip_graph_post_id(post: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in post.items() if key != "id"}


def _serialize_datetime(value: dt.datetime | None) -> int | None:
    if value is None:
        return None
    return int(value.timestamp())


def _to_timestamp(value: Any) -> int:
    if isinstance(value, dt.datetime):
        return int(value.timestamp())
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _to_datetime(value: Any) -> dt.datetime | None:
    if isinstance(value, dt.datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=dt.UTC)
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(value, tz=dt.UTC)
    return None


def _build_period_posts_metrics(posts: list[dict[str, Any]], members_count: int | None) -> dict[str, Any] | None:
    if not posts:
        return None

    dates = [_to_datetime(post.get("date")) for post in posts]
    dates = [date for date in dates if date is not None]
    period_start = min(dates) if dates else None
    period_end = max(dates) if dates else None
    days = max(((period_end - period_start).days + 1) if period_start and period_end else 1, 1)

    total_likes = sum(post.get("likes", 0) for post in posts)
    total_views = sum(post.get("views", 0) for post in posts)
    total_comments = sum(post.get("comments", 0) for post in posts)
    total_reposts = sum(post.get("reposts", 0) for post in posts)
    total_text_len = sum(post.get("text_len", 0) for post in posts)
    posts_count = len(posts)
    members = members_count or 0
    total_engagements = total_likes + total_comments + total_reposts

    return {
        "total_likes": total_likes,
        "total_views": total_views,
        "total_comments": total_comments,
        "total_reposts": total_reposts,
        "total_text_len": total_text_len,
        "avg_likes": round(total_likes / posts_count, 3),
        "avg_views": round(total_views / posts_count, 3),
        "avg_comments": round(total_comments / posts_count, 3),
        "avg_reposts": round(total_reposts / posts_count, 3),
        "avg_text_len": round(total_text_len / posts_count, 3),
        "period_posts_count": posts_count,
        "post_rate": round(posts_count / days, 3),
        "engagement_rate": round((total_engagements / members) * 100, 3) if members > 0 else 0.0,
        "views_rate": round(total_views / days, 3),
        "daily_engagement_rate": round((total_engagements / days) / members * 100, 3) if members > 0 else 0.0,
        "talk_rate": round(total_comments / members * 100, 3) if members > 0 else 0.0,
        "love_rate": round(total_likes / members * 100, 3) if members > 0 else 0.0,
    }
