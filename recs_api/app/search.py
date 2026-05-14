from __future__ import annotations

from opensearchpy import AsyncOpenSearch


class SearchService:
    """Async wrapper around OpenSearch for the resource_documents index."""

    INDEX = "resource_documents"

    def __init__(self, os_url: str) -> None:
        self.client = AsyncOpenSearch(
            hosts=[os_url],
            use_ssl=False,
            verify_certs=False,
        )

    async def search_resources(
        self,
        query: str,
        *,
        min_audience: int | None = None,
        category: str | None = None,
        platform: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """
        Full-text BM25 search with optional filters.

        Returns raw OpenSearch hits (list of dicts with ``_id``, ``_score``,
        ``_source``).
        """
        filters: list[dict] = []
        if min_audience is not None:
            filters.append({"range": {"audience_size": {"gte": min_audience}}})
        if category is not None:
            filters.append({"term": {"category": category}})
        if platform is not None:
            filters.append({"term": {"platform": platform}})

        body: dict = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "title^3",
                                    "description^2",
                                    "topic_keywords",
                                ],
                                "type": "best_fields",
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
            "size": limit,
        }

        response = await self.client.search(index=self.INDEX, body=body)
        return response["hits"]["hits"]

    async def close(self) -> None:
        await self.client.close()
