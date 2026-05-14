from __future__ import annotations

import datetime as dt

from src.VkParser.models import GroupRow, PostRow
from src.VkParser.vk_raw_types import VkGroupInfoRaw, VkWallPostRaw


def extract_group_row(group: VkGroupInfoRaw) -> GroupRow:
    cover = group.get("cover") if isinstance(group, dict) else None
    cover_url: str | None = None
    if isinstance(cover, dict) and cover.get("enabled"):
        images = cover.get("images") or []
        if isinstance(images, list) and images:
            # ``cover.images`` is sorted from lowest to highest resolution —
            # grab the largest so the UI doesn't have to upscale.
            largest = images[-1]
            if isinstance(largest, dict):
                cover_url = largest.get("url")

    return GroupRow(
        id=group["id"],
        name=group.get("name"),
        screen_name=group.get("screen_name"),
        members_count=group.get("members_count"),
        photo_url=group.get("photo_200") or group.get("photo_100") or group.get("photo_50"),
        cover_url=cover_url,
    )


def extract_post_row(post: VkWallPostRaw) -> PostRow:
    owner_id = post.get("owner_id")
    group_id = abs(owner_id) if isinstance(owner_id, int) else None

    date_ts = post.get("date")
    edited_ts = post.get("edited")

    text = post.get("text") or ""

    return PostRow(
        id=post["id"],
        len_message=len(text),
        repost_count=(post.get("reposts") or {}).get("count", 0),
        view_count=(post.get("views") or {}).get("count", 0),
        comments_count=(post.get("comments") or {}).get("count", 0),
        message_timestamp=dt.datetime.fromtimestamp(date_ts) if date_ts else None,
        edit_date=dt.datetime.fromtimestamp(edited_ts) if edited_ts else None,
        reactions_count=(post.get("likes") or {}).get("count", 0),
        id_groups=group_id,
    )
