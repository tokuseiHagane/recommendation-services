from __future__ import annotations

from decimal import Decimal

from piccolo.columns import ForeignKey, Integer, Numeric, Text, Timestamp, Varchar
from piccolo.columns.column_types import JSONB, Serial
from piccolo.columns.defaults.timestamp import TimestampNow
from piccolo.table import Table

from shared.db import DB
from shared.models.normalized import ResourceDocument


class RecommendationRequest(Table, tablename="recommendation_requests", db=DB):
    id: Serial
    query = Text()
    min_audience = Integer(null=True, default=None)
    category = Varchar(length=100, null=True, default=None)
    platform = Varchar(length=50, null=True, default=None)
    limit = Integer(default=20)
    created_at = Timestamp(default=TimestampNow())


class RecommendationCandidate(Table, tablename="recommendation_candidates", db=DB):
    id: Serial
    request = ForeignKey(references=RecommendationRequest)
    doc_id = Varchar(length=255)
    search_score = Numeric(digits=(10, 4), default=Decimal("0"))
    source_data = JSONB(null=True, default=None)
    created_at = Timestamp(default=TimestampNow())


class RecommendationResult(Table, tablename="recommendation_results", db=DB):
    id: Serial
    request = ForeignKey(references=RecommendationRequest)
    candidate = ForeignKey(references=RecommendationCandidate)
    rank = Integer()
    final_score = Numeric(digits=(10, 4), default=Decimal("0"))
    explanation = Text(default="")


class RecommendationFeedback(Table, tablename="recommendation_feedback", db=DB):
    id: Serial
    result = ForeignKey(references=RecommendationResult)
    rating = Integer(null=True, default=None)
    comment = Text(null=True, default=None)
    created_at = Timestamp(default=TimestampNow())


class IndexSyncLog(Table, db=DB, tablename="index_sync_log"):
    id: Serial
    document = ForeignKey(references=ResourceDocument)
    status = Varchar(length=16)
    error_message = Text(null=True, default=None)
    synced_at = Timestamp()
