"""CachedPeriod model — tracks which date ranges have been parsed per group."""

from piccolo.columns import Integer, Serial, Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.table import Table


class CachedPeriod(Table, tablename="cached_periods"):
    """Record of a successfully parsed date range for a VK group.

    Used by CacheCheckTask to determine which periods are already
    available and which must still be fetched from VK API.
    """

    id = Serial(primary_key=True)
    group_id = Integer(null=False, index=True, help_text="FK to groups.id")
    period_start = Timestamptz(null=False)
    period_end = Timestamptz(null=False)
    parsed_at = Timestamptz(default=TimestamptzNow())
    posts_count = Integer(default=0)
