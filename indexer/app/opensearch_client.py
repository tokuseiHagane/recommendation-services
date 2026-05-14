from __future__ import annotations

import logging
from typing import Any

from opensearchpy import AsyncOpenSearch, helpers

logger = logging.getLogger(__name__)

RESOURCE_DOCUMENTS_MAPPING: dict[str, Any] = {
    "mappings": {
        "properties": {
            "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "description": {"type": "text"},
            "topic_keywords": {"type": "text"},
            "platform": {"type": "keyword"},
            "audience_size": {"type": "integer"},
            "avg_views": {"type": "float"},
            "engagement_rate": {"type": "float"},
            "category": {"type": "keyword"},
            "last_updated": {"type": "date"},
            "source_community_id": {"type": "keyword"},
        }
    }
}


class OpenSearchClient:
    def __init__(self, url: str) -> None:
        self.client = AsyncOpenSearch(
            hosts=[url],
            use_ssl=False,
            verify_certs=False,
        )

    async def ensure_index(self, index_name: str, mapping: dict[str, Any]) -> None:
        """Create index if not exists with given mapping."""
        exists = await self.client.indices.exists(index=index_name)
        if not exists:
            await self.client.indices.create(index=index_name, body=mapping)
            logger.info("Created index %s", index_name)

    async def bulk_index(
        self, index_name: str, documents: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Bulk index documents. Returns {success_count, failed_ids}."""
        if not documents:
            return {"success_count": 0, "failed_ids": []}

        actions = [
            {
                "_index": index_name,
                "_id": doc.pop("_id"),
                "_source": doc,
            }
            for doc in documents
        ]

        success_count, errors = await helpers.async_bulk(
            self.client,
            actions,
            raise_on_error=False,
            raise_on_exception=False,
        )

        failed_ids: list[str] = []
        if errors:
            for err in errors:
                info = err.get("index", {})
                doc_id = info.get("_id")
                reason = info.get("error", {})
                if doc_id:
                    failed_ids.append(doc_id)
                logger.error("Bulk index error for %s: %s", doc_id, reason)

        return {"success_count": success_count, "failed_ids": failed_ids}

    async def close(self) -> None:
        await self.client.close()
