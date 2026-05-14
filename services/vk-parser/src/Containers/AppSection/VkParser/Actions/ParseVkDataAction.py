"""ParseVkDataAction — orchestrate the broker-first VK parsing flow."""

from datetime import UTC, datetime
from typing import Any

import logfire

from src.Containers.AppSection.VkParser.Data.Dto import VkParseRequest
from src.Containers.AppSection.VkParser.Tasks.CacheCheckTask import CacheCheckInput, CacheCheckTask
from src.Containers.AppSection.VkParser.Tasks.FetchVkWallTask import FetchVkWallInput, FetchVkWallTask
from src.Containers.AppSection.VkParser.Tasks.FindGroupsTask import FindGroupsInput, FindGroupsTask
from src.Containers.AppSection.VkParser.Tasks.FindPostsTask import FindPostsInput, FindPostsTask
from src.Containers.AppSection.VkParser.Tasks.PublishToKafkaTask import PublishToKafkaInput, PublishToKafkaTask
from src.Containers.AppSection.VkParser.Tasks.SaveParsedDataTask import SaveParsedDataInput, SaveParsedDataTask
from src.Ship.Configs.App import AppSettings
from src.Ship.Parents.Action import Action
from src.VkParser.sorting import sort_posts


def _extract_screen_names(links: list[str]) -> list[str]:
    """Extract VK screen_name / domain from links like https://vk.com/lentach."""
    names: list[str] = []
    for link in links:
        link = link.rstrip("/")
        if "/" in link:
            names.append(link.rsplit("/", 1)[-1])
        else:
            names.append(link)
    return names


class ParseVkDataAction(Action[tuple[str, VkParseRequest], dict[str, Any]]):
    """Orchestrate VK parsing: cache read → parse gaps → publish → merge → respond."""

    def __init__(
        self,
        fetch_vk_wall_task: FetchVkWallTask,
        cache_check_task: CacheCheckTask,
        publish_to_kafka_task: PublishToKafkaTask,
        save_parsed_data_task: SaveParsedDataTask,
        find_groups_task: FindGroupsTask,
        find_posts_task: FindPostsTask,
        settings: AppSettings,
    ) -> None:
        self._fetch_vk_wall = fetch_vk_wall_task
        self._cache_check = cache_check_task
        self._publish_kafka = publish_to_kafka_task
        self._save_data = save_parsed_data_task
        self._find_groups = find_groups_task
        self._find_posts = find_posts_task
        self._settings = settings

    async def run(self, data: tuple[str, VkParseRequest]) -> dict[str, Any]:
        vk_token, request = data

        logfire.info(
            "Starting VK parse",
            links_count=len(request.links),
            start_date=str(request.start_date),
            end_date=str(request.end_date),
            top_n=request.top_n,
            parse_all=request.parse_all,
        )

        sort_params_dict = _build_sort_params_dict(request)
        screen_names = _extract_screen_names(request.links)

        cache_result = await self._cache_check.execute(
            CacheCheckInput(
                screen_names=screen_names,
                start_date=request.start_date,
                end_date=request.end_date,
                parse_all=request.parse_all,
            )
        )
        cached_result = await self._build_response_from_cache(
            screen_names=screen_names,
            request=request,
            sort_params=sort_params_dict,
        )

        fresh_result: dict[str, Any] = {}
        for link, name in zip(request.links, screen_names, strict=True):
            for period in cache_result.missing_periods.get(name, []):
                fresh_period_result = await self._fetch_vk_wall.execute(
                    FetchVkWallInput(
                        vk_token=vk_token,
                        links=[link],
                        start_date=period.start,
                        end_date=period.end,
                        top_n=request.top_n,
                        sort_params=sort_params_dict,
                    )
                )

                fresh_domain = fresh_period_result.get(name)
                if fresh_domain:
                    fresh_result[name] = (
                        _merge_domain_payloads(
                            fresh_result[name],
                            fresh_domain,
                            top_n=request.top_n,
                            sort_params=sort_params_dict,
                        )
                        if name in fresh_result
                        else fresh_domain
                    )

                groups_flat, posts_flat = _flatten_parsed_result(fresh_period_result)
                # Raw posts are an internal channel between service.py and this
                # action — strip them from the per-domain payload so they don't
                # leak into the client response alongside top_posts/graph_data.
                if isinstance(fresh_domain, dict):
                    fresh_domain.pop("posts", None)
                if not groups_flat and not posts_flat:
                    continue

                try:
                    await self._save_data.execute(
                        SaveParsedDataInput(
                            groups=groups_flat,
                            posts=posts_flat,
                            period_start=period.start,
                            period_end=period.end,
                        )
                    )
                except Exception:
                    logfire.warning("SaveParsedDataTask failed, continuing", screen_name=name, exc_info=True)

                try:
                    await self._publish_kafka.execute(
                        PublishToKafkaInput(
                            groups=groups_flat,
                            posts=posts_flat,
                            kafka_bootstrap_servers=self._settings.kafka_bootstrap_servers,
                            kafka_groups_topic=self._settings.kafka_groups_topic,
                            kafka_posts_topic_prefix=self._settings.kafka_posts_topic_prefix,
                        )
                    )
                except Exception:
                    logfire.warning("PublishToKafkaTask failed, continuing", screen_name=name, exc_info=True)

        final_result: dict[str, Any] = {}
        for screen_name in screen_names:
            cached_domain = cached_result.get(screen_name)
            fresh_domain = fresh_result.get(screen_name)
            if cached_domain and fresh_domain:
                final_result[screen_name] = _merge_domain_payloads(
                    cached_domain,
                    fresh_domain,
                    top_n=request.top_n,
                    sort_params=sort_params_dict,
                )
            elif fresh_domain:
                final_result[screen_name] = fresh_domain
            elif cached_domain:
                final_result[screen_name] = cached_domain

        logfire.info("VK parse completed", domains_parsed=len(final_result))
        return final_result

    async def _build_response_from_cache(
        self,
        *,
        screen_names: list[str],
        request: VkParseRequest,
        sort_params: dict[str, Any],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        for screen_name in screen_names:
            groups = await self._find_groups.execute(FindGroupsInput(screen_name=screen_name, limit=1, offset=0))
            if not groups:
                continue

            group = groups[0]
            posts = await self._find_posts.execute(
                FindPostsInput(
                    group_id=group["id"],
                    start_date=request.start_date,
                    end_date=request.end_date,
                    limit=None,
                    offset=0,
                )
            )
            result[screen_name] = _build_domain_response(
                group=group,
                posts=posts,
                top_n=request.top_n,
                sort_params=sort_params,
            )

        return result


def _build_sort_params_dict(request: VkParseRequest) -> dict[str, Any]:
    sort_params_dict: dict[str, Any] = {}
    for field_name in ("date", "engagement_rate", "views", "comments", "reposts"):
        param = getattr(request.sort_params, field_name)
        sort_params_dict[field_name] = {"priority": param.priority, "reverse": param.reverse}
    return sort_params_dict


def _flatten_parsed_result(result: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Extract group metadata and posts from the legacy parser output."""
    groups: list[dict[str, Any]] = []
    posts: list[dict[str, Any]] = []

    for _domain, domain_data in result.items():
        if not isinstance(domain_data, dict):
            continue

        wall = domain_data.get("wall_info") or domain_data
        group_id = wall.get("id")
        if group_id:
            groups.append(
                {
                    "id": int(group_id),
                    "name": wall.get("name"),
                    "screen_name": wall.get("screen_name"),
                    "members_count": wall.get("members_count"),
                    "photo_url": wall.get("photo_url"),
                    "cover_url": wall.get("cover_url"),
                }
            )

        domain_posts = domain_data.get("posts") or domain_data.get("all_posts") or []
        for post in domain_posts:
            if not isinstance(post, dict):
                continue
            post_id = post.get("id")
            if not post_id:
                continue
            posts.append(
                {
                    "id": int(post_id),
                    "id_groups": int(group_id) if group_id else None,
                    "message_timestamp": post.get("date") or post.get("message_timestamp"),
                    "edit_date": post.get("edit_date"),
                    "view_count": post.get("views", {}).get("count", 0)
                    if isinstance(post.get("views"), dict)
                    else post.get("view_count", 0),
                    "reactions_count": post.get("likes", {}).get("count", 0)
                    if isinstance(post.get("likes"), dict)
                    else post.get("reactions_count", 0),
                    "comments_count": post.get("comments", {}).get("count", 0)
                    if isinstance(post.get("comments"), dict)
                    else post.get("comments_count", 0),
                    "repost_count": post.get("reposts", {}).get("count", 0)
                    if isinstance(post.get("reposts"), dict)
                    else post.get("repost_count", 0),
                    "len_message": len(post.get("text", "")) if post.get("text") else post.get("len_message", 0),
                }
            )

    return groups, posts


def _build_domain_response(
    *,
    group: dict[str, Any],
    posts: list[dict[str, Any]],
    top_n: int,
    sort_params: dict[str, Any],
) -> dict[str, Any]:
    graph_posts = [_build_graph_post(post) for post in posts]
    sorted_posts = _sort_graph_posts(graph_posts, sort_params=sort_params)
    return {
        "id": group.get("id"),
        "name": group.get("name"),
        "screen_name": group.get("screen_name"),
        "members_count": group.get("members_count"),
        "posts_count": len(sorted_posts),
        "top_posts": [post.copy() for post in sorted_posts[:top_n]],
        "down_posts": [post.copy() for post in reversed(sorted_posts[-top_n:])] if sorted_posts else [],
        "graph_data": [_strip_graph_post_id(post) for post in sorted_posts],
        "period_posts_metrics": _build_period_posts_metrics(sorted_posts, group.get("members_count")),
    }


def _merge_domain_payloads(
    left_payload: dict[str, Any],
    right_payload: dict[str, Any],
    *,
    top_n: int,
    sort_params: dict[str, Any],
) -> dict[str, Any]:
    merged_graph_posts = _merge_graph_posts(
        _posts_from_graph_data(left_payload.get("graph_data", [])),
        _posts_from_graph_data(right_payload.get("graph_data", [])),
    )
    merged_sorted_graph_posts = _sort_graph_posts(merged_graph_posts, sort_params=sort_params)
    members_count = right_payload.get("members_count", left_payload.get("members_count"))

    return {
        "id": right_payload.get("id", left_payload.get("id")),
        "name": right_payload.get("name", left_payload.get("name")),
        "screen_name": right_payload.get("screen_name", left_payload.get("screen_name")),
        "members_count": members_count,
        "posts_count": len(merged_sorted_graph_posts),
        "top_posts": _select_top_posts(
            left_payload.get("top_posts", []),
            right_payload.get("top_posts", []),
            top_n=top_n,
            sort_params=sort_params,
        ),
        "down_posts": _select_down_posts(
            left_payload.get("down_posts", []),
            right_payload.get("down_posts", []),
            top_n=top_n,
            sort_params=sort_params,
        ),
        "graph_data": [_strip_graph_post_id(post) for post in merged_sorted_graph_posts],
        "period_posts_metrics": _build_period_posts_metrics(merged_sorted_graph_posts, members_count),
    }


def _build_graph_post(post: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": post.get("id"),
        "date": _serialize_datetime(post.get("message_timestamp")),
        "edit_date": _serialize_datetime(post.get("edit_date")),
        "views": post.get("view_count", 0),
        "likes": post.get("reactions_count", 0),
        "comments": post.get("comments_count", 0),
        "reposts": post.get("repost_count", 0),
        "text_len": post.get("len_message", 0),
    }


def _posts_from_graph_data(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_normalize_post(post) for post in posts]


def _normalize_post(post: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": post.get("id"),
        "date": _serialize_datetime(post.get("date") or post.get("message_timestamp")),
        "edit_date": _serialize_datetime(post.get("edit_date")),
        "views": _unwrap_counter(post.get("views"), fallback=post.get("view_count", 0)),
        "likes": _unwrap_counter(post.get("likes"), fallback=post.get("reactions_count", 0)),
        "comments": _unwrap_counter(post.get("comments"), fallback=post.get("comments_count", 0)),
        "reposts": _unwrap_counter(post.get("reposts"), fallback=post.get("repost_count", 0)),
        "text_len": post.get("text_len", post.get("len_message", 0)),
    }


def _unwrap_counter(value: Any, *, fallback: int = 0) -> int:
    if isinstance(value, dict):
        return int(value.get("count", 0))
    if value is None:
        return int(fallback)
    return int(value)


def _serialize_datetime(value: Any) -> Any:
    if isinstance(value, datetime):
        return int(value.timestamp())
    return value


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


def _merge_graph_posts(left_posts: list[dict[str, Any]], right_posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    for post in [*_dedupe_posts(left_posts), *_dedupe_posts(right_posts)]:
        merged[_post_signature(post)] = post
    return list(merged.values())


def _dedupe_posts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[Any, ...], dict[str, Any]] = {}
    for post in posts:
        normalized = _normalize_post(post)
        seen[_post_signature(normalized)] = normalized
    return list(seen.values())


def _post_signature(post: dict[str, Any]) -> tuple[Any, ...]:
    return (
        post.get("id"),
        _to_timestamp(post.get("date")),
        _to_timestamp(post.get("edit_date")),
        post.get("views", 0),
        post.get("likes", 0),
        post.get("comments", 0),
        post.get("reposts", 0),
        post.get("text_len", 0),
    )


def _select_top_posts(
    left_posts: list[dict[str, Any]],
    right_posts: list[dict[str, Any]],
    *,
    top_n: int,
    sort_params: dict[str, Any],
) -> list[dict[str, Any]]:
    merged_candidates = _dedupe_posts([*_posts_from_graph_data(left_posts), *_posts_from_graph_data(right_posts)])
    return _sort_graph_posts(merged_candidates, sort_params=sort_params)[:top_n]


def _select_down_posts(
    left_posts: list[dict[str, Any]],
    right_posts: list[dict[str, Any]],
    *,
    top_n: int,
    sort_params: dict[str, Any],
) -> list[dict[str, Any]]:
    merged_candidates = _dedupe_posts([*_posts_from_graph_data(left_posts), *_posts_from_graph_data(right_posts)])
    sorted_posts = _sort_graph_posts(merged_candidates, sort_params=sort_params)
    return [post.copy() for post in reversed(sorted_posts[-top_n:])] if sorted_posts else []


def _strip_graph_post_id(post: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in post.items() if key != "id"}


def _to_timestamp(value: Any) -> int:
    if isinstance(value, datetime):
        return int(value.timestamp())
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _to_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
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
