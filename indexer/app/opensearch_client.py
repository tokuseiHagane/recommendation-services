from __future__ import annotations

from opensearchpy import OpenSearch

from shared.config import settings


def get_opensearch_client() -> OpenSearch:
    return OpenSearch(
        hosts=[settings.OPENSEARCH_URL],
        use_ssl=False,
        verify_certs=False,
    )
