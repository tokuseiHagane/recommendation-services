from __future__ import annotations


def rank_candidates(hits: list[dict], *, top_n: int | None = None) -> list[dict]:
    """
    Re-rank OpenSearch hits using a composite score.

    ``composite = 0.5 * search_norm + 0.2 * audience_norm
                + 0.2 * engagement_norm + 0.1 * freshness_norm``

    Returns a sorted list of dicts ready for persistence and API response.
    If *top_n* is given, only the first *top_n* items are returned.
    """
    if not hits:
        return []

    max_search_score = max(h["_score"] for h in hits) or 1.0

    results: list[dict] = []
    for hit in hits:
        src = hit["_source"]

        search_norm = hit["_score"] / max_search_score

        audience = src.get("audience_size") or 0
        audience_norm = min(audience / 100_000, 1.0)

        engagement = src.get("engagement_rate") or 0.0
        engagement_norm = min(engagement / 0.1, 1.0)

        freshness_norm = 0.5

        final_score = (
            0.5 * search_norm
            + 0.2 * audience_norm
            + 0.2 * engagement_norm
            + 0.1 * freshness_norm
        )

        results.append(
            {
                "doc_id": hit["_id"],
                "final_score": round(final_score, 4),
                "search_score": hit["_score"],
                "source": src,
                "explanation": (
                    f"search={search_norm:.2f}, "
                    f"audience={audience_norm:.2f}, "
                    f"engagement={engagement_norm:.2f}, "
                    f"freshness={freshness_norm:.2f}"
                ),
            }
        )

    results.sort(key=lambda x: x["final_score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    if top_n is not None:
        results = results[:top_n]

    return results
