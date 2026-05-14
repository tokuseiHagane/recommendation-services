"""CacheCheckTask — determine cached and missing periods for a group."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import logfire

from src.Containers.AppSection.VkParser.Models.CachedPeriod import CachedPeriod
from src.Containers.AppSection.VkParser.Models.VkGroup import VkGroup
from src.Ship.Parents.Task import Task


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime


@dataclass
class CacheCheckInput:
    screen_names: list[str]
    start_date: datetime
    end_date: datetime
    parse_all: bool = False


@dataclass
class CacheCheckResult:
    cached_periods: dict[str, list[Period]] = field(default_factory=dict)
    missing_periods: dict[str, list[Period]] = field(default_factory=dict)
    group_ids: dict[str, int] = field(default_factory=dict)
    force_full_parse: dict[str, bool] = field(default_factory=dict)


class CacheCheckTask(Task[CacheCheckInput, CacheCheckResult]):
    """Analyse PostgreSQL ``cached_periods`` table and decide what to parse."""

    async def run(self, data: CacheCheckInput) -> CacheCheckResult:
        result = CacheCheckResult()

        for screen_name in data.screen_names:
            group_row = (
                await VkGroup.select(VkGroup.id, VkGroup.last_parsed_at)
                .where(VkGroup.screen_name == screen_name)
                .first()
            )

            if not group_row:
                result.missing_periods[screen_name] = [Period(start=data.start_date, end=data.end_date)]
                result.force_full_parse[screen_name] = True
                logfire.debug("Group not in cache, full parse needed", screen_name=screen_name)
                continue

            group_id = group_row["id"]
            result.group_ids[screen_name] = group_id

            if data.parse_all:
                last_parsed = group_row.get("last_parsed_at")
                if last_parsed is None or (datetime.now().astimezone() - last_parsed).total_seconds() > 86400:
                    result.missing_periods[screen_name] = [Period(start=data.start_date, end=data.end_date)]
                    result.force_full_parse[screen_name] = True
                    logfire.debug("parse_all active, data stale", screen_name=screen_name)
                    continue

            rows = (
                await CachedPeriod.select(CachedPeriod.period_start, CachedPeriod.period_end)
                .where(
                    (CachedPeriod.group_id == group_id)
                    & (CachedPeriod.period_start <= data.end_date)
                    & (CachedPeriod.period_end >= data.start_date)
                )
                .order_by(CachedPeriod.period_start)
            )

            cached = [Period(start=row["period_start"], end=row["period_end"]) for row in rows]
            missing = calculate_missing_periods(
                request_start=data.start_date,
                request_end=data.end_date,
                cached_periods=cached,
            )

            result.cached_periods[screen_name] = cached
            result.missing_periods[screen_name] = missing
            result.force_full_parse[screen_name] = not cached and bool(missing)

        return result


def calculate_missing_periods(
    *,
    request_start: datetime,
    request_end: datetime,
    cached_periods: list[Period],
) -> list[Period]:
    """Calculate uncovered gaps using inclusive cache intervals."""

    epsilon = timedelta(microseconds=1)
    missing: list[Period] = []
    current = request_start

    for period in sorted(cached_periods, key=lambda item: item.start):
        period_start = max(period.start, request_start)
        period_end = min(period.end, request_end)
        if period_end < request_start or period_start > request_end:
            continue

        gap_end = period_start - epsilon
        if current <= gap_end:
            missing.append(Period(start=current, end=gap_end))

        current = max(current, period_end + epsilon)
        if current > request_end:
            break

    if current <= request_end:
        missing.append(Period(start=current, end=request_end))

    return missing
