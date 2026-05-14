"""SaveParsedDataTask — upsert groups, posts, and cached_periods into PostgreSQL."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import logfire

from src.Containers.AppSection.VkParser.Models.CachedPeriod import CachedPeriod
from src.Containers.AppSection.VkParser.Models.VkGroup import VkGroup
from src.Containers.AppSection.VkParser.Models.VkPost import VkPost
from src.Ship.Parents.Task import Task


@dataclass
class SaveParsedDataInput:
    groups: list[dict[str, Any]]
    posts: list[dict[str, Any]]
    period_start: datetime
    period_end: datetime


class SaveParsedDataTask(Task[SaveParsedDataInput, int]):
    """Persist parsed groups + posts into the local cache DB.

    Returns the number of posts upserted.
    """

    async def run(self, data: SaveParsedDataInput) -> int:
        saved_posts = 0
        now = datetime.now().astimezone()

        for g in data.groups:
            group_id = g.get("id")
            if not group_id:
                continue

            exists = await VkGroup.exists().where(VkGroup.id == group_id)
            # ``photo_url``/``cover_url`` are optional in the parser payload —
            # only overwrite the cached value when VK actually returned a URL,
            # so we don't nuke a previously-saved avatar on a partial fetch.
            photo_url = g.get("photo_url")
            cover_url = g.get("cover_url")
            update_payload: dict[Any, Any] = {
                VkGroup.name: g.get("name"),
                VkGroup.screen_name: g.get("screen_name"),
                VkGroup.members_count: g.get("members_count"),
                VkGroup.last_parsed_at: now,
            }
            if photo_url:
                update_payload[VkGroup.photo_url] = photo_url
            if cover_url:
                update_payload[VkGroup.cover_url] = cover_url

            if exists:
                await VkGroup.update(update_payload).where(VkGroup.id == group_id)
            else:
                await VkGroup.insert(
                    VkGroup(
                        id=group_id,
                        name=g.get("name"),
                        screen_name=g.get("screen_name"),
                        members_count=g.get("members_count"),
                        last_parsed_at=now,
                        photo_url=photo_url,
                        cover_url=cover_url,
                    )
                )

            logfire.debug("Upserted VkGroup", group_id=group_id, name=g.get("name"))

        for p in data.posts:
            post_id = p.get("id")
            if not post_id:
                continue

            exists = await VkPost.exists().where(VkPost.id == post_id)
            if exists:
                await VkPost.update(
                    {
                        VkPost.view_count: p.get("view_count", 0),
                        VkPost.reactions_count: p.get("reactions_count", 0),
                        VkPost.comments_count: p.get("comments_count", 0),
                        VkPost.repost_count: p.get("repost_count", 0),
                        VkPost.len_message: p.get("len_message", 0),
                        VkPost.edit_date: p.get("edit_date"),
                    }
                ).where(VkPost.id == post_id)
            else:
                await VkPost.insert(
                    VkPost(
                        id=post_id,
                        id_groups=p.get("id_groups"),
                        message_timestamp=p.get("message_timestamp"),
                        edit_date=p.get("edit_date"),
                        view_count=p.get("view_count", 0),
                        reactions_count=p.get("reactions_count", 0),
                        comments_count=p.get("comments_count", 0),
                        repost_count=p.get("repost_count", 0),
                        len_message=p.get("len_message", 0),
                    )
                )
            saved_posts += 1

        for g in data.groups:
            group_id = g.get("id")
            if not group_id:
                continue
            group_post_count = sum(1 for p in data.posts if p.get("id_groups") == group_id)
            exists = await CachedPeriod.exists().where(
                (CachedPeriod.group_id == group_id)
                & (CachedPeriod.period_start == data.period_start)
                & (CachedPeriod.period_end == data.period_end)
            )
            if exists:
                await CachedPeriod.update(
                    {
                        CachedPeriod.posts_count: group_post_count,
                        CachedPeriod.parsed_at: now,
                    }
                ).where(
                    (CachedPeriod.group_id == group_id)
                    & (CachedPeriod.period_start == data.period_start)
                    & (CachedPeriod.period_end == data.period_end)
                )
                continue

            await CachedPeriod.insert(
                CachedPeriod(
                    group_id=group_id,
                    period_start=data.period_start,
                    period_end=data.period_end,
                    parsed_at=now,
                    posts_count=group_post_count,
                )
            )

        logfire.info(
            "Saved parsed data",
            groups_count=len(data.groups),
            posts_count=saved_posts,
        )
        return saved_posts
