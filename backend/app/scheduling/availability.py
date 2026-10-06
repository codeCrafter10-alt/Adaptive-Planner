from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.scheduling.models import AvailabilityWindow, ExistingScheduleBlock


@dataclass(frozen=True)
class WeeklyAvailability:
    day_of_week: int
    start_time: time
    end_time: time

    def __post_init__(self) -> None:
        if not 0 <= self.day_of_week <= 6:
            raise ValueError("day_of_week must be between 0 and 6 (Monday=0)")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")


@dataclass(frozen=True)
class AvailabilityExceptionInput:
    date: date
    is_available: bool
    start_time: time | None = None
    end_time: time | None = None

    def __post_init__(self) -> None:
        if self.is_available:
            if self.start_time is None or self.end_time is None:
                raise ValueError(
                    "available exceptions require start_time and end_time"
                )
            if self.start_time >= self.end_time:
                raise ValueError("start_time must be before end_time")
        elif self.start_time is not None or self.end_time is not None:
            raise ValueError(
                "unavailable exceptions must not have start_time or end_time"
            )


def generate_availability_windows(
    weekly_availability: list[WeeklyAvailability],
    exceptions: list[AvailabilityExceptionInput],
    existing_schedule: list[ExistingScheduleBlock],
    scheduling_start: datetime,
    scheduling_end: datetime,
    timezone_name: str,
) -> list[AvailabilityWindow]:
    """Return free UTC windows after existing scheduled work is subtracted.

    Later scheduling phases must not subtract ``existing_schedule`` again.
    """
    zone = _load_timezone(timezone_name)
    start_utc = _as_utc(scheduling_start)
    end_utc = _as_utc(scheduling_end)
    if start_utc >= end_utc:
        raise ValueError("scheduling_start must be before scheduling_end")

    exception_by_date: dict[date, AvailabilityExceptionInput] = {}
    for exception in exceptions:
        if exception.date in exception_by_date:
            raise ValueError(f"duplicate availability exception date: {exception.date}")
        exception_by_date[exception.date] = exception

    local_start = start_utc.astimezone(zone).date()
    local_end = end_utc.astimezone(zone).date()
    candidates: list[tuple[datetime, datetime]] = []
    current = local_start
    while current <= local_end:
        intervals = _intervals_for_date(current, weekly_availability, exception_by_date)
        for start_time, end_time in intervals:
            start = _local_to_utc(current, start_time, zone)
            end = _local_to_utc(current, end_time, zone)
            start = max(start, start_utc)
            end = min(end, end_utc)
            if start < end:
                candidates.append((start, end))
        current += timedelta(days=1)

    occupied = sorted(
        (_as_utc(block.start), _as_utc(block.end)) for block in existing_schedule
    )
    merged_occupied: list[tuple[datetime, datetime]] = []
    for start, end in occupied:
        if merged_occupied and start < merged_occupied[-1][1]:
            merged_occupied[-1] = (
                merged_occupied[-1][0],
                max(merged_occupied[-1][1], end),
            )
        else:
            merged_occupied.append((start, end))

    result: list[AvailabilityWindow] = []
    for candidate_start, candidate_end in sorted(candidates):
        cursor = candidate_start
        for occupied_start, occupied_end in merged_occupied:
            if occupied_end <= cursor:
                continue
            if occupied_start >= candidate_end:
                break
            if occupied_start > cursor:
                result.append(
                    AvailabilityWindow(
                        start=cursor,
                        end=min(occupied_start, candidate_end),
                    )
                )
            cursor = max(cursor, occupied_end)
            if cursor >= candidate_end:
                break
        if cursor < candidate_end:
            result.append(AvailabilityWindow(start=cursor, end=candidate_end))
    return result


def _intervals_for_date(
    current: date,
    weekly: list[WeeklyAvailability],
    exceptions: dict[date, AvailabilityExceptionInput],
) -> list[tuple[time, time]]:
    exception = exceptions.get(current)
    if exception is not None:
        if not exception.is_available:
            return []
        assert exception.start_time is not None
        assert exception.end_time is not None
        return [(exception.start_time, exception.end_time)]

    intervals = sorted(
        (
            item.start_time,
            item.end_time,
        )
        for item in weekly
        if item.day_of_week == current.weekday()
    )
    merged: list[tuple[time, time]] = []
    for start, end in intervals:
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _load_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown IANA timezone: {timezone_name}") from exc


def _local_to_utc(day: date, local_time: time, zone: ZoneInfo) -> datetime:
    # zoneinfo assigns the pre-transition offset to nonexistent times with fold=0;
    # converting that value to UTC produces the normalized post-gap instant.
    local = datetime.combine(day, local_time).replace(tzinfo=zone, fold=0)
    return local.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc)
