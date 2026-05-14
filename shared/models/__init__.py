from shared.models.etl import TgChannel, TgPost, VkGroup, VkPost
from shared.models.normalized import (
    AdResource,
    ResourceCategory,
    ResourceDocument,
    ResourceMetricSnapshot,
    ResourceTopicProfile,
    SourcePlatform,
)
from shared.models.recommendations import (
    IndexSyncLog,
    RecommendationCandidate,
    RecommendationFeedback,
    RecommendationRequest,
    RecommendationResult,
)

__all__ = [
    # ETL (readonly)
    "VkGroup",
    "VkPost",
    "TgChannel",
    "TgPost",
    # Normalized
    "SourcePlatform",
    "AdResource",
    "ResourceCategory",
    "ResourceTopicProfile",
    "ResourceMetricSnapshot",
    "ResourceDocument",
    # Recommendations
    "RecommendationRequest",
    "RecommendationCandidate",
    "RecommendationResult",
    "RecommendationFeedback",
    "IndexSyncLog",
]
