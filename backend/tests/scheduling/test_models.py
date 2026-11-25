from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.models.task import TaskPriority
from app.scheduling.models import (
    AvailabilityWindow,
    ExistingScheduleBlock,
    ScheduleBlock,
    SchedulingInput,
    SchedulingResult,
    SchedulingTask,
    UnscheduledWork,
)
from app.scheduling.availability import (
    AvailabilityExceptionInput,
    WeeklyAvailability,
    generate_availability_windows,
)


START = datetime(2026, 9, 25, 9, 0, tzinfo=timezone.utc)
END = datetime(2026, 9, 25, 17, 0, tzinfo=timezone.utc)


def _task(**overrides):
    values = {
        "task_id": 1,
        "remaining_duration_minutes": 60,
        "minimum_session_length_minutes": 15,
        "priority": TaskPriority.medium,
        "deadline": END,
    }
    values.update(overrides)
    return SchedulingTask(**values)


def test_valid_scheduling_models_preserve_fields():
    task = _task()
    availability = AvailabilityWindow(start=START, end=END)
    existing = ExistingScheduleBlock(start=START, end=END)
    block = ScheduleBlock(task_id=1, start=START, end=END)
    unscheduled = UnscheduledWork(task_id=1, remaining_duration_minutes=30)
    scheduling_input = SchedulingInput(
        tasks=[task],
        availability=[availability],
        existing_schedule=[existing],
        scheduling_start=START,
        scheduling_end=END,
    )
    result = SchedulingResult(blocks=[block], unscheduled_work=[unscheduled])

    assert task.remaining_duration_minutes == 60
    assert task.minimum_session_length_minutes == 15
    assert scheduling_input.scheduling_start == START
    assert result.blocks == [block]
    assert result.unscheduled_work == [unscheduled]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("remaining_duration_minutes", 0),
        ("remaining_duration_minutes", -1),
        ("minimum_session_length_minutes", 0),
        ("minimum_session_length_minutes", -1),
    ],
)
def test_scheduling_task_rejects_invalid_durations(field, value):
    with pytest.raises(ValidationError):
        _task(**{field: value})


def test_scheduling_task_rejects_minimum_session_longer_than_remaining():
    with pytest.raises(ValidationError):
        _task(remaining_duration_minutes=15, minimum_session_length_minutes=30)


def test_unscheduled_work_requires_positive_remaining_duration():
    with pytest.raises(ValidationError):
        UnscheduledWork(task_id=1, remaining_duration_minutes=0)


@pytest.mark.parametrize(
    "model",
    [
        lambda: AvailabilityWindow(start=END, end=START),
        lambda: ExistingScheduleBlock(start=END, end=START),
        lambda: ScheduleBlock(task_id=1, start=END, end=START),
        lambda: SchedulingInput(
            tasks=[],
            availability=[],
            existing_schedule=[],
            scheduling_start=END,
            scheduling_end=START,
        ),
    ],
)
def test_models_reject_invalid_time_ranges(model):
    with pytest.raises(ValidationError):
        model()


def test_models_reject_timezone_naive_datetimes():
    naive_start = datetime(2026, 9, 25, 9, 0)
    naive_end = datetime(2026, 9, 25, 17, 0)

    with pytest.raises(ValidationError):
        AvailabilityWindow(start=naive_start, end=naive_end)

    with pytest.raises(ValidationError):
        _task(deadline=naive_end)


def test_datetime_fields_normalize_to_utc_before_comparison():
    zone = ZoneInfo("America/New_York")
    start = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    end = datetime(2026, 11, 1, 1, 10, tzinfo=zone, fold=1)

    window = AvailabilityWindow(start=start, end=end)
    task = _task(deadline=end)
    existing = ExistingScheduleBlock(start=start, end=end)
    block = ScheduleBlock(task_id=1, start=start, end=end)
    scheduling_input = SchedulingInput(
        tasks=[task],
        availability=[window],
        existing_schedule=[existing],
        scheduling_start=start,
        scheduling_end=datetime(2026, 11, 1, 2, 0, tzinfo=zone, fold=1),
    )

    assert window.start.tzinfo is timezone.utc
    assert window.end.tzinfo is timezone.utc
    assert window.start < window.end
    assert task.deadline.tzinfo is timezone.utc
    assert existing.start.tzinfo is timezone.utc
    assert block.end.tzinfo is timezone.utc
    assert scheduling_input.scheduling_start.tzinfo is timezone.utc
    assert window.end - window.start == timedelta(minutes=40)


def test_fall_back_overlapping_availability_windows_are_rejected_by_utc_instants():
    zone = ZoneInfo("America/New_York")
    first = AvailabilityWindow(
        start=datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0),
        end=datetime(2026, 11, 1, 1, 10, tzinfo=zone, fold=1),
    )
    second = AvailabilityWindow(
        start=datetime(2026, 11, 1, 1, 0, tzinfo=zone, fold=1),
        end=datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=1),
    )

    with pytest.raises(ValidationError, match="overlap"):
        SchedulingInput(
            tasks=[],
            availability=[first, second],
            existing_schedule=[],
            scheduling_start=datetime(2026, 11, 1, 0, tzinfo=zone, fold=0),
            scheduling_end=datetime(2026, 11, 2, 0, tzinfo=zone, fold=0),
        )


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 9, 25, 9, 0, 1, tzinfo=timezone.utc),
        datetime(2026, 9, 25, 9, 0, 0, 1, tzinfo=timezone.utc),
    ],
)
def test_scheduling_bounds_and_availability_require_whole_minutes(value):
    with pytest.raises(ValidationError):
        AvailabilityWindow(start=value, end=END)

    with pytest.raises(ValidationError):
        SchedulingInput(
            tasks=[],
            availability=[],
            existing_schedule=[],
            scheduling_start=value,
            scheduling_end=END,
        )


def test_whole_minute_precision_is_checked_after_utc_normalization():
    zone = ZoneInfo("Africa/Abidjan")
    local_start = datetime(1900, 1, 1, 12, 0, tzinfo=zone)
    local_end = datetime(1900, 1, 1, 13, 0, tzinfo=zone)

    assert local_start.utcoffset().total_seconds() % 60 != 0
    with pytest.raises(ValidationError, match="whole minutes"):
        AvailabilityWindow(start=local_start, end=local_end)


def test_deadlines_and_existing_blocks_allow_sub_minute_precision():
    deadline = datetime(2026, 9, 25, 10, 0, 59, tzinfo=timezone.utc)
    existing_end = datetime(2026, 9, 25, 10, 0, 59, tzinfo=timezone.utc)

    assert _task(deadline=deadline).deadline == deadline
    assert ExistingScheduleBlock(start=START, end=existing_end).end == existing_end


def test_scheduling_input_rejects_duplicate_task_ids():
    with pytest.raises(ValidationError, match="unique"):
        SchedulingInput(
            tasks=[_task(task_id=1), _task(task_id=1)],
            availability=[],
            existing_schedule=[],
            scheduling_start=START,
            scheduling_end=END,
        )


def test_scheduling_input_accepts_unsorted_adjacent_windows():
    input_model = SchedulingInput(
        tasks=[],
        availability=[
            AvailabilityWindow(
                start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                end=datetime(2026, 9, 25, 11, tzinfo=timezone.utc),
            ),
            AvailabilityWindow(start=START, end=datetime(2026, 9, 25, 10, tzinfo=timezone.utc)),
        ],
        existing_schedule=[],
        scheduling_start=START,
        scheduling_end=END,
    )

    assert len(input_model.availability) == 2


@pytest.mark.parametrize(
    "second",
    [
        (
            datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 9, 25, 9, 30, tzinfo=timezone.utc),
            datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 9, 25, 9, tzinfo=timezone.utc),
            datetime(2026, 9, 25, 11, tzinfo=timezone.utc),
        ),
    ],
)
def test_scheduling_input_rejects_overlapping_availability_windows(second):
    first = AvailabilityWindow(start=START, end=datetime(2026, 9, 25, 11, tzinfo=timezone.utc))
    second = AvailabilityWindow(start=second[0], end=second[1])
    with pytest.raises(ValidationError, match="overlap"):
        SchedulingInput(
            tasks=[],
            availability=[first, second],
            existing_schedule=[],
            scheduling_start=START,
            scheduling_end=END,
        )


def test_scheduling_input_allows_overlapping_existing_schedule_blocks():
    SchedulingInput(
        tasks=[],
        availability=[],
        existing_schedule=[
            ExistingScheduleBlock(start=START, end=datetime(2026, 9, 25, 11, tzinfo=timezone.utc)),
            ExistingScheduleBlock(
                start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                end=datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
            ),
        ],
        scheduling_start=START,
        scheduling_end=END,
    )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: WeeklyAvailability(0, time(9, 0, 1), time(10)),
        lambda: AvailabilityExceptionInput(
            datetime(2026, 9, 25).date(),
            True,
            time(9),
            time(10, 0, 0, 1),
        ),
    ],
)
def test_availability_time_inputs_require_whole_minutes(factory):
    with pytest.raises(ValueError, match="whole minutes"):
        factory()


@pytest.mark.parametrize(
    ("weekly", "timezone_name", "start", "end"),
    [
        (
            [WeeklyAvailability(6, time(2, 30), time(5))],
            "America/New_York",
            datetime(2026, 3, 8, tzinfo=timezone.utc),
            datetime(2026, 3, 9, tzinfo=timezone.utc),
        ),
        (
            [WeeklyAvailability(6, time(1), time(4))],
            "America/New_York",
            datetime(2026, 11, 1, tzinfo=timezone.utc),
            datetime(2026, 11, 2, tzinfo=timezone.utc),
        ),
    ],
)
def test_real_dst_generated_windows_are_valid_scheduling_input(
    weekly, timezone_name, start, end
):
    windows = generate_availability_windows(
        weekly, [], [], start, end, timezone_name
    )

    model = SchedulingInput(
        tasks=[],
        availability=windows,
        existing_schedule=[],
        scheduling_start=start,
        scheduling_end=end,
    )

    assert model.availability == windows


def test_priority_reuses_existing_task_priority():
    task = _task(priority=TaskPriority.high)

    assert task.priority is TaskPriority.high

    with pytest.raises(ValidationError):
        _task(priority="urgent")
