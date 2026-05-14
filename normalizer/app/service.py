from __future__ import annotations

import logging
from datetime import UTC, datetime

from shared.models.etl import VkGroup, VkPost
from shared.models.normalized import (
    AdResource,
    ResourceDocument,
    ResourceMetricSnapshot,
    ResourceTopicProfile,
    SourcePlatform,
)

logger = logging.getLogger(__name__)


async def _ensure_vk_platform() -> int:
    """Return the id of the 'vk' SourcePlatform, creating it if needed."""
    await SourcePlatform.insert(
        SourcePlatform(name="vk"),
    ).on_conflict(action="DO NOTHING").run()

    row = (
        await SourcePlatform.select(SourcePlatform.id)
        .where(SourcePlatform.name == "vk")
        .first()
        .run()
    )
    if not row:
        msg = "Failed to resolve SourcePlatform 'vk'"
        raise RuntimeError(msg)
    return row["id"]


async def _upsert_ad_resource(
    platform_id: int,
    external_id: str,
    name: str,
    screen_name: str,
    now: datetime,
) -> int:
    """Upsert AdResource and return its id."""
    url = f"https://vk.com/{screen_name}" if screen_name else ""
    record = AdResource(
        source_platform=platform_id,
        external_id=external_id,
        name=name,
        url=url,
        created_at=now,
        updated_at=now,
    )
    await (
        AdResource.insert(record)
        .on_conflict(
            action="DO UPDATE",
            target=AdResource.external_id,
            values=[AdResource.name, AdResource.url, AdResource.updated_at],
        )
        .run()
    )
    row = (
        await AdResource.select(AdResource.id)
        .where(AdResource.external_id == external_id)
        .first()
        .run()
    )
    if not row:
        msg = f"Failed to resolve AdResource external_id={external_id}"
        raise RuntimeError(msg)
    return row["id"]


async def _insert_metric_snapshot(
    resource_id: int,
    posts: list[dict],
    members_count: int,
    now: datetime,
) -> dict:
    """Calculate metrics from posts, insert a snapshot, and return the metrics."""
    total_views = sum(p.get("view_count") or 0 for p in posts)
    total_reactions = sum(p.get("reactions_count") or 0 for p in posts)
    avg_views = total_views / len(posts) if posts else 0.0
    engagement_rate = (total_reactions / total_views) if total_views > 0 else 0.0

    snapshot = ResourceMetricSnapshot(
        resource=resource_id,
        avg_views=avg_views,
        engagement_rate=engagement_rate,
        subscribers_count=members_count,
        snapshot_at=now,
    )
    await ResourceMetricSnapshot.insert(snapshot).run()
    return {
        "avg_views": avg_views,
        "engagement_rate": engagement_rate,
    }


async def _upsert_topic_profile(
    resource_id: int,
    group_name: str,
    screen_name: str,
    now: datetime,
) -> None:
    keywords = ",".join(filter(None, [group_name, screen_name]))
    profile = ResourceTopicProfile(
        resource=resource_id,
        topic_keywords=keywords,
        updated_at=now,
    )
    await (
        ResourceTopicProfile.insert(profile)
        .on_conflict(
            action="DO UPDATE",
            target=ResourceTopicProfile.resource,
            values=[ResourceTopicProfile.topic_keywords, ResourceTopicProfile.updated_at],
        )
        .run()
    )


async def _upsert_document(
    resource_id: int,
    group_name: str,
    screen_name: str,
    members_count: int,
    metrics: dict,
    now: datetime,
) -> None:
    keywords = ",".join(filter(None, [group_name, screen_name]))
    description = f"Группа ВКонтакте: {group_name}, подписчики: {members_count}"
    content = (
        f"name: {group_name}\n"
        f"screen_name: {screen_name}\n"
        f"subscribers: {members_count}\n"
        f"avg_views: {metrics['avg_views']:.1f}\n"
        f"engagement_rate: {metrics['engagement_rate']:.6f}\n"
        f"keywords: {keywords}"
    )

    existing = (
        await ResourceDocument.select(ResourceDocument.version)
        .where(ResourceDocument.resource == resource_id)
        .first()
        .run()
    )
    new_version = (existing["version"] + 1) if existing else 1

    doc = ResourceDocument(
        resource=resource_id,
        title=group_name,
        description=description,
        content=content,
        version=new_version,
        updated_at=now,
    )
    await (
        ResourceDocument.insert(doc)
        .on_conflict(
            action="DO UPDATE",
            target=ResourceDocument.resource,
            values=[
                ResourceDocument.title,
                ResourceDocument.description,
                ResourceDocument.content,
                ResourceDocument.version,
                ResourceDocument.updated_at,
            ],
        )
        .run()
    )


async def normalize_cycle() -> int:
    """Main normalization cycle — called on schedule.

    Returns the number of groups processed.
    """
    now = datetime.now(UTC)
    platform_id = await _ensure_vk_platform()

    groups = await VkGroup.select().run()
    processed = 0

    for group in groups:
        group_id: int = group["id"]
        group_name: str = group.get("name") or ""
        screen_name: str = group.get("screen_name") or ""
        members_count: int = group.get("members_count") or 0
        external_id = str(group_id)

        posts = (
            await VkPost.select(VkPost.view_count, VkPost.reactions_count)
            .where(VkPost.id_groups == group_id)
            .run()
        )
        if not posts:
            continue

        resource_id = await _upsert_ad_resource(
            platform_id, external_id, group_name, screen_name, now,
        )

        metrics = await _insert_metric_snapshot(
            resource_id, posts, members_count, now,
        )

        await _upsert_topic_profile(resource_id, group_name, screen_name, now)

        await _upsert_document(
            resource_id, group_name, screen_name, members_count, metrics, now,
        )

        processed += 1

    logger.info("Normalization complete: processed %d groups out of %d", processed, len(groups))
    return processed
