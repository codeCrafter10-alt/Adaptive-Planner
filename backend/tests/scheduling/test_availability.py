from datetime import date, datetime, time, timedelta, timezone

import pytest
from zoneinfo import ZoneInfo

from app.scheduling.availability import (
    AvailabilityExceptionInput,
    WeeklyAvailability,
    generate_availability_windows,
)
from app.scheduling.models import ExistingScheduleBlock


def test_generates_utc_windows_and_subtracts_middle_block():
    windows = generate_availability_windows(
        [WeeklyAvailability(0, time(9), time(17))],
        [],
        [
            ExistingScheduleBlock(
                start=datetime(2026, 9, 28, 12, tzinfo=timezone.utc),
                end=datetime(2026, 9, 28, 13, tzinfo=timezone.utc),
            )
        ],
        datetime(2026, 9, 28, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 29, 0, tzinfo=timezone.utc),
        "UTC",
    )

    assert [(window.start.hour, window.end.hour) for window in windows] == [
        (9, 12),
        (13, 17),
    ]


def test_available_exception_replaces_weekly_and_adjacent_blocks_stay_separate():
    windows = generate_availability_windows(
        [
            WeeklyAvailability(0, time(9), time(12)),
            WeeklyAvailability(0, time(12), time(17)),
        ],
        [
            AvailabilityExceptionInput(
                date(2026, 9, 28),
                is_available=True,
                start_time=time(13),
                end_time=time(14),
            )
        ],
        [],
        datetime(2026, 9, 28, tzinfo=timezone.utc),
        datetime(2026, 9, 29, tzinfo=timezone.utc),
        "UTC",
    )

    assert [(window.start.hour, window.end.hour) for window in windows] == [(13, 14)]


def test_duplicate_exception_dates_and_unknown_timezone_raise_value_error():
    exception = AvailabilityExceptionInput(date(2026, 9, 28), False)
    with pytest.raises(ValueError, match="duplicate"):
        generate_availability_windows(
            [],
            [exception, exception],
            [],
            datetime(2026, 9, 28, tzinfo=timezone.utc),
            datetime(2026, 9, 29, tzinfo=timezone.utc),
            "UTC",
        )

    with pytest.raises(ValueError, match="unknown IANA timezone"):
        generate_availability_windows(
            [],
            [],
            [],
            datetime(2026, 9, 28, tzinfo=timezone.utc),
            datetime(2026, 9, 29, tzinfo=timezone.utc),
            "Not/A-Timezone",
        )


def test_overlapping_weekly_blocks_merge_but_adjacent_blocks_remain_separate():
    windows = generate_availability_windows(
        [
            WeeklyAvailability(0, time(9), time(13)),
            WeeklyAvailability(0, time(12), time(15)),
            WeeklyAvailability(0, time(15), time(17)),
        ],
        [],
        [],
        datetime(2026, 9, 28, tzinfo=timezone.utc),
        datetime(2026, 9, 29, tzinfo=timezone.utc),
        "UTC",
    )

    assert [(window.start.hour, window.end.hour) for window in windows] == [
        (9, 15),
        (15, 17),
    ]


def test_bounds_are_clipped_and_end_is_exclusive():
    windows = generate_availability_windows(
        [WeeklyAvailability(0, time(9), time(17))],
        [],
        [],
        datetime(2026, 9, 28, 12, tzinfo=timezone.utc),
        datetime(2026, 9, 28, 15, tzinfo=timezone.utc),
        "UTC",
    )

    assert [(window.start.hour, window.end.hour) for window in windows] == [(12, 15)]


def test_touching_and_overlapping_existing_blocks_do_not_create_gaps():
    windows = generate_availability_windows(
        [WeeklyAvailability(0, time(9), time(17))],
        [],
        [
            ExistingScheduleBlock(
                start=datetime(2026, 9, 28, 10, tzinfo=timezone.utc),
                end=datetime(2026, 9, 28, 12, tzinfo=timezone.utc),
            ),
            ExistingScheduleBlock(
                start=datetime(2026, 9, 28, 11, tzinfo=timezone.utc),
                end=datetime(2026, 9, 28, 13, tzinfo=timezone.utc),
            ),
            ExistingScheduleBlock(
                start=datetime(2026, 9, 28, 13, tzinfo=timezone.utc),
                end=datetime(2026, 9, 28, 14, tzinfo=timezone.utc),
            ),
        ],
        datetime(2026, 9, 28, tzinfo=timezone.utc),
        datetime(2026, 9, 29, tzinfo=timezone.utc),
        "UTC",
    )

    assert [(window.start.hour, window.end.hour) for window in windows] == [
        (9, 10),
        (14, 17),
    ]


def test_existing_schedule_datetimes_are_converted_to_utc_before_subtraction():
    windows = generate_availability_windows(
        [WeeklyAvailability(0, time(9), time(17))],
        [],
        [
            ExistingScheduleBlock(
                start=datetime(
                    2026,
                    9,
                    28,
                    12,
                    tzinfo=ZoneInfo("America/New_York"),
                ),
                end=datetime(
                    2026,
                    9,
                    28,
                    13,
                    tzinfo=ZoneInfo("America/New_York"),
                ),
            )
        ],
        datetime(2026, 9, 28, tzinfo=timezone.utc),
        datetime(2026, 9, 29, tzinfo=timezone.utc),
        "UTC",
    )

    assert [(window.start.hour, window.end.hour) for window in windows] == [(9, 16)]


def test_local_dates_are_resolved_before_utc_clipping():
    windows = generate_availability_windows(
        [WeeklyAvailability(0, time(0), time(2))],
        [],
        [],
        datetime(2026, 9, 28, 6, tzinfo=timezone.utc),
        datetime(2026, 9, 29, 6, tzinfo=timezone.utc),
        "America/Los_Angeles",
    )

    assert [(window.start, window.end) for window in windows] == [
        (
            datetime(2026, 9, 28, 7, tzinfo=timezone.utc),
            datetime(2026, 9, 28, 9, tzinfo=timezone.utc),
        )
    ]


def test_spring_forward_gap_normalizes_and_discards_whole_gap():
    windows = generate_availability_windows(
        [WeeklyAvailability(6, time(2), time(3))],
        [],
        [],
        datetime(2026, 3, 8, tzinfo=timezone.utc),
        datetime(2026, 3, 9, tzinfo=timezone.utc),
        "America/New_York",
    )
    assert windows == []

    windows = generate_availability_windows(
        [WeeklyAvailability(6, time(2, 30), time(5))],
        [],
        [],
        datetime(2026, 3, 8, tzinfo=timezone.utc),
        datetime(2026, 3, 9, tzinfo=timezone.utc),
        "America/New_York",
    )
    assert [(window.start, window.end) for window in windows] == [
        (
            datetime(2026, 3, 8, 7, 30, tzinfo=timezone.utc),
            datetime(2026, 3, 8, 9, tzinfo=timezone.utc),
        )
    ]


def test_fall_back_uses_earlier_ambiguous_occurrence_and_true_duration():
    windows = generate_availability_windows(
        [WeeklyAvailability(6, time(1), time(4))],
        [],
        [],
        datetime(2026, 11, 1, tzinfo=timezone.utc),
        datetime(2026, 11, 2, tzinfo=timezone.utc),
        "America/New_York",
    )

    assert windows[0].start == datetime(2026, 11, 1, 5, tzinfo=timezone.utc)
    assert windows[0].end == datetime(2026, 11, 1, 9, tzinfo=timezone.utc)
    assert windows[0].end - windows[0].start == timedelta(hours=4)


def test_unavailable_exception_removes_the_whole_local_day():
    windows = generate_availability_windows(
        [WeeklyAvailability(0, time(9), time(17))],
        [AvailabilityExceptionInput(date(2026, 9, 28), False)],
        [],
        datetime(2026, 9, 28, tzinfo=timezone.utc),
        datetime(2026, 9, 29, tzinfo=timezone.utc),
        "UTC",
    )

    assert windows == []


def test_exception_matches_local_calendar_date_not_utc_date():
    windows = generate_availability_windows(
        [WeeklyAvailability(6, time(23), time(23, 59))],
        [AvailabilityExceptionInput(date(2026, 9, 27), False)],
        [],
        datetime(2026, 9, 28, tzinfo=timezone.utc),
        datetime(2026, 9, 28, 8, tzinfo=timezone.utc),
        "America/Los_Angeles",
    )

    assert windows == []


def test_scheduling_end_at_local_midnight_is_exclusive():
    windows = generate_availability_windows(
        [WeeklyAvailability(1, time(0), time(1))],
        [],
        [],
        datetime(2026, 9, 28, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 29, 7, tzinfo=timezone.utc),
        "America/Los_Angeles",
    )

    assert windows == []


def test_multi_day_range_clips_midday_start_and_end():
    windows = generate_availability_windows(
        [
            WeeklyAvailability(0, time(9), time(17)),
            WeeklyAvailability(1, time(9), time(17)),
        ],
        [],
        [],
        datetime(2026, 9, 28, 12, tzinfo=timezone.utc),
        datetime(2026, 9, 29, 15, tzinfo=timezone.utc),
        "UTC",
    )

    assert [(window.start.hour, window.end.hour) for window in windows] == [
        (12, 17),
        (9, 15),
    ]


def test_invalid_weekly_and_exception_shapes_raise_value_error():
    with pytest.raises(ValueError, match="day_of_week"):
        WeeklyAvailability(7, time(9), time(10))
    with pytest.raises(ValueError, match="before"):
        WeeklyAvailability(0, time(10), time(9))
    with pytest.raises(ValueError, match="require"):
        AvailabilityExceptionInput(date(2026, 9, 28), True)
    with pytest.raises(ValueError, match="must not"):
        AvailabilityExceptionInput(
            date(2026, 9, 28), False, time(9), time(10)
        )
    with pytest.raises(ValueError, match="before"):
        AvailabilityExceptionInput(
            date(2026, 9, 28), True, time(10), time(9)
        )


def test_invalid_bounds_and_naive_datetime_raise_value_error():
    with pytest.raises(ValueError, match="before"):
        generate_availability_windows(
            [],
            [],
            [],
            datetime(2026, 9, 29, tzinfo=timezone.utc),
            datetime(2026, 9, 28, tzinfo=timezone.utc),
            "UTC",
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        generate_availability_windows(
            [],
            [],
            [],
            datetime(2026, 9, 28),
            datetime(2026, 9, 29, tzinfo=timezone.utc),
            "UTC",
        )


def test_ambiguous_one_thirty_uses_first_fall_back_occurrence():
    windows = generate_availability_windows(
        [WeeklyAvailability(6, time(1, 30), time(2))],
        [],
        [],
        datetime(2026, 11, 1, tzinfo=timezone.utc),
        datetime(2026, 11, 2, tzinfo=timezone.utc),
        "America/New_York",
    )

    assert windows[0].start == datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc)


def test_containment_and_overlap_chains_merge_weekly_blocks():
    windows = generate_availability_windows(
        [
            WeeklyAvailability(0, time(9), time(17)),
            WeeklyAvailability(0, time(10), time(11)),
            WeeklyAvailability(0, time(12), time(16)),
            WeeklyAvailability(0, time(14), time(18)),
        ],
        [],
        [],
        datetime(2026, 9, 28, tzinfo=timezone.utc),
        datetime(2026, 9, 29, tzinfo=timezone.utc),
        "UTC",
    )

    assert [(window.start.hour, window.end.hour) for window in windows] == [(9, 18)]


def test_existing_blocks_outside_and_straddling_bounds_are_clipped():
    windows = generate_availability_windows(
        [WeeklyAvailability(0, time(9), time(17))],
        [],
        [
            ExistingScheduleBlock(
                start=datetime(2026, 9, 28, 8, tzinfo=timezone.utc),
                end=datetime(2026, 9, 28, 11, tzinfo=timezone.utc),
            ),
            ExistingScheduleBlock(
                start=datetime(2026, 9, 28, 15, tzinfo=timezone.utc),
                end=datetime(2026, 9, 28, 18, tzinfo=timezone.utc),
            ),
        ],
        datetime(2026, 9, 28, 10, tzinfo=timezone.utc),
        datetime(2026, 9, 28, 16, tzinfo=timezone.utc),
        "UTC",
    )

    assert [(window.start.hour, window.end.hour) for window in windows] == [(11, 15)]


def test_inputs_are_not_mutated():
    weekly = [WeeklyAvailability(0, time(9), time(17))]
    exceptions = [AvailabilityExceptionInput(date(2026, 9, 28), False)]
    existing = [
        ExistingScheduleBlock(
            start=datetime(2026, 9, 28, 12, tzinfo=timezone.utc),
            end=datetime(2026, 9, 28, 13, tzinfo=timezone.utc),
        )
    ]
    original = (weekly[:], exceptions[:], existing[:])

    generate_availability_windows(
        weekly,
        exceptions,
        existing,
        datetime(2026, 9, 28, tzinfo=timezone.utc),
        datetime(2026, 9, 29, tzinfo=timezone.utc),
        "UTC",
    )

    assert (weekly, exceptions, existing) == original


def test_shuffled_input_order_produces_deterministic_output():
    weekly = [
        WeeklyAvailability(0, time(13), time(17)),
        WeeklyAvailability(0, time(9), time(12)),
        WeeklyAvailability(1, time(9), time(12)),
        WeeklyAvailability(2, time(9), time(12)),
    ]
    existing = [
        ExistingScheduleBlock(
            start=datetime(2026, 9, 28, 10, tzinfo=timezone.utc),
            end=datetime(2026, 9, 28, 11, tzinfo=timezone.utc),
        ),
        ExistingScheduleBlock(
            start=datetime(2026, 9, 28, 15, tzinfo=timezone.utc),
            end=datetime(2026, 9, 28, 16, tzinfo=timezone.utc),
        ),
    ]
    exceptions = [
        AvailabilityExceptionInput(
            date(2026, 9, 30),
            is_available=False,
        ),
        AvailabilityExceptionInput(
            date(2026, 10, 1),
            is_available=True,
            start_time=time(10),
            end_time=time(12),
        )
    ]
    bounds = (
        datetime(2026, 9, 28, tzinfo=timezone.utc),
        datetime(2026, 10, 2, tzinfo=timezone.utc),
    )

    first = generate_availability_windows(
        weekly, exceptions, existing, *bounds, "UTC"
    )
    second = generate_availability_windows(
        list(reversed(weekly)),
        list(reversed(exceptions)),
        list(reversed(existing)),
        *bounds,
        "UTC",
    )

    assert first == second
