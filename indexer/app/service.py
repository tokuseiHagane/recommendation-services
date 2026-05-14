from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from shared.models.normalized import (
    AdResource,
    ResourceDocument,
    ResourceMetricSnapshot,
    ResourceTopicProfile,
    SourcePlatform,
)
from shared.models.recommendations import IndexSyncLog

from indexer.app.opensearch_client import OpenSearchClient

logger = logging.getLogger(__name__)

INDEX_NAME = "resource_documents"


async def _build_opensearch_doc(row: dict[str, Any]) -> dict[str, Any]:
    """Build a denormalized OpenSearch document by joining related tables."""
    doc_id = str(row["id"])
    resource_id = row["resource"]

    resource = (
        await AdResource.select()
        .where(AdResource.id == resource_id)
        .first()
        .run()
    )

    platform_name = None
    if resource:
        platform = (
            await SourcePlatform.select()
            .where(SourcePlatform.id == resource["source_platform"])
            .first()
            .run()
        )
        platform_name = platform["name"] if platform else None

    metrics = (
        await ResourceMetricSnapshot.select()
        .where(ResourceMetricSnapshot.resource == resource_id)
        .order_by(ResourceMetricSnapshot.snapshot_at, ascending=False)
        .first()
        .run()
    )

    topic = (
        await ResourceTopicProfile.select()
        .where(ResourceTopicProfile.resource == resource_id)
        .first()
        .run()
    )

    updated_at = row.get("updated_at")
    if isinstance(updated_at, datetime):
        updated_at = updated_at.isoformat()

    return {
        "_id": doc_id,
        "title": row.get("title", ""),
        "description": row.get("description", ""),
        "topic_keywords": topic.get("topic_keywords", "") if topic else "",
        "platform": platform_name,
        "audience_size": metrics.get("subscribers_count", 0) if metrics else 0,
        "avg_views": float(metrics.get("avg_views", 0)) if metrics else 0.0,
        "engagement_rate": float(metrics.get("engagement_rate", 0)) if metrics else 0.0,
        "category": None,
        "last_updated": updated_at,
        "source_community_id": resource.get("external_id") if resource else None,
    }


async def sync_cycle(os_client: OpenSearchClient) -> dict[str, Any]:
    """Main sync cycle: DB -> OpenSearch -> update synced_at -> write logs."""
    now = datetime.now(timezone.utc)

    rows = (
        await ResourceDocument.select()
        .where(
            ResourceDocument.synced_at.is_null()
            | (ResourceDocument.synced_at < ResourceDocument.updated_at)
        )
        .run()
    )

    if not rows:
        logger.info("No documents to sync")
        return {"synced": 0, "failed": 0}

    logger.info("Found %d documents to sync", len(rows))

    documents = [await _build_opensearch_doc(row) for row in rows]
    doc_id_map = {str(row["id"]): row for row in rows}

    result = await os_client.bulk_index(INDEX_NAME, documents)
    failed_ids = set(result["failed_ids"])

    success_ids = [did for did in doc_id_map if did not in failed_ids]
    if success_ids:
        await (
            ResourceDocument.update({ResourceDocument.synced_at: now})
            .where(ResourceDocument.id.is_in([int(sid) for sid in success_ids]))
            .run()
        )

    log_entries = []
    for doc_id in doc_id_map:
        status = "failed" if doc_id in failed_ids else "success"
        error_msg = "bulk index error" if doc_id in failed_ids else None
        log_entries.append(
            IndexSyncLog(
                document=int(doc_id),
                status=status,
                error_message=error_msg,
                synced_at=now,
            )
        )

    if log_entries:
        await IndexSyncLog.insert(*log_entries).run()

    logger.info(
        "Sync complete: %d success, %d failed",
        len(success_ids),
        len(failed_ids),
    )
    return {"synced": len(success_ids), "failed": len(failed_ids)}
