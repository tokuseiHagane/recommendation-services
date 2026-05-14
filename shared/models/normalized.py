from __future__ import annotations

from decimal import Decimal

from piccolo.columns import ForeignKey, Integer, Numeric, Text, Timestamp, Varchar
from piccolo.columns.column_types import Serial
from piccolo.columns.defaults.timestamp import TimestampNow
from piccolo.table import Table

from shared.db import DB


class SourcePlatform(Table, tablename="source_platforms", db=DB):
    id: Serial
    name = Varchar(length=50, unique=True)


class ResourceCategory(Table, tablename="resource_categories", db=DB):
    id: Serial
    name = Varchar(length=100, unique=True)


class AdResource(Table, tablename="ad_resources", db=DB):
    id: Serial
    source_platform = ForeignKey(references=SourcePlatform)
    external_id = Varchar(length=255, unique=True)
    name = Varchar(length=500, default="")
    url = Varchar(length=1000, default="")
    created_at = Timestamp(default=TimestampNow())
    updated_at = Timestamp(default=TimestampNow())


class ResourceTopicProfile(Table, tablename="resource_topic_profiles", db=DB):
    id: Serial
    resource = ForeignKey(references=AdResource, unique=True)
    topic_keywords = Text(default="")
    updated_at = Timestamp(default=TimestampNow())


class ResourceMetricSnapshot(Table, tablename="resource_metric_snapshots", db=DB):
    id: Serial
    resource = ForeignKey(references=AdResource)
    avg_views = Numeric(digits=(12, 2), default=Decimal("0"))
    engagement_rate = Numeric(digits=(8, 6), default=Decimal("0"))
    subscribers_count = Integer(default=0)
    snapshot_at = Timestamp(default=TimestampNow())


class ResourceDocument(Table, tablename="resource_documents", db=DB):
    id: Serial
    resource = ForeignKey(references=AdResource, unique=True)
    title = Varchar(length=500, default="")
    description = Text(default="")
    content = Text(default="")
    version = Integer(default=1)
    updated_at = Timestamp(default=TimestampNow())
    synced_at = Timestamp(null=True, default=None)
