from __future__ import annotations

import logging
from dataclasses import dataclass, field

from litestar import MediaType, Request, get, post

from recs_api.app.ranker import rank_candidates
from recs_api.app.search import SearchService
from shared.models.recommendations import (
    RecommendationCandidate,
    RecommendationRequest,
    RecommendationResult,
)

logger = logging.getLogger(__name__)


@dataclass
class RecommendRequestDTO:
    query: str
    min_audience: int | None = None
    category: str | None = None
    platform: str | None = None
    limit: int = 20


@dataclass
class RecommendResultItem:
    rank: int
    doc_id: str
    final_score: float
    search_score: float
    explanation: str
    source: dict = field(default_factory=dict)


@dataclass
class RecommendResponseDTO:
    request_id: int
    query: str
    results: list[RecommendResultItem]
    total: int


@post("/recommend", media_type=MediaType.JSON)
async def recommend(data: RecommendRequestDTO, request: Request) -> RecommendResponseDTO:
    """
    Full recommendation pipeline:
    1. Persist the request
    2. Search OpenSearch via SearchService
    3. Rank candidates with composite score
    4. Persist candidates and top-N results
    5. Return ranked recommendations
    """
    search_svc: SearchService = request.app.state.search_service

    rec_request = RecommendationRequest(
        query=data.query,
        min_audience=data.min_audience,
        category=data.category,
        platform=data.platform,
        limit=data.limit,
    )
    await rec_request.save()
    request_id: int = rec_request.id  # type: ignore[assignment]

    hits = await search_svc.search_resources(
        data.query,
        min_audience=data.min_audience,
        category=data.category,
        platform=data.platform,
        limit=data.limit,
    )

    ranked = rank_candidates(hits, top_n=data.limit)

    candidate_id_map: dict[str, int] = {}
    for hit in hits:
        cand = RecommendationCandidate(
            request=request_id,
            doc_id=hit["_id"],
            search_score=hit["_score"],
            source_data=hit["_source"],
        )
        await cand.save()
        candidate_id_map[hit["_id"]] = cand.id  # type: ignore[assignment]

    for item in ranked:
        cand_id = candidate_id_map.get(item["doc_id"])
        if cand_id is None:
            continue
        result = RecommendationResult(
            request=request_id,
            candidate=cand_id,
            rank=item["rank"],
            final_score=item["final_score"],
            explanation=item["explanation"],
        )
        await result.save()

    response_items = [
        RecommendResultItem(
            rank=r["rank"],
            doc_id=r["doc_id"],
            final_score=r["final_score"],
            search_score=r["search_score"],
            explanation=r["explanation"],
            source=r["source"],
        )
        for r in ranked
    ]

    logger.info(
        "recommend request_id=%s query=%r candidates=%d results=%d",
        request_id,
        data.query,
        len(hits),
        len(response_items),
    )

    return RecommendResponseDTO(
        request_id=request_id,
        query=data.query,
        results=response_items,
        total=len(response_items),
    )


@get("/health", media_type=MediaType.JSON)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "recs-api"}
