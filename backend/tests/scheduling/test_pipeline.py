from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.models.task import TaskPriority
from app.scheduling import (
    AvailabilityExceptionInput,
    ExistingScheduleBlock,
    SchedulingResult,
    SchedulingTask,
    WeeklyAvailability,
    generate_availability_windows,
    schedule_with_availability,
)
import app.scheduling.pipeline as pipeline


def _utc(year, month, day, hour=0, minute=0, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _task(
    task_id,
    remaining_duration_minutes=60,
    minimum_session_length_minutes=15,
    priority=TaskPriority.medium,
    deadline=None,
):
    return SchedulingTask(
        task_id=task_id,
        remaining_duration_minutes=remaining_duration_minutes,
        minimum_session_length_minutes=minimum_session_length_minutes,
        priority=priority,
        deadline=deadline or _utc(2026, 9, 29),
    )


def _schedule(
    tasks,
    *,
    weekly_availability,
    exceptions=None,
    existing_schedule=None,
    scheduling_start,
    scheduling_end,
    timezone_name="UTC",
):
    return schedule_with_availability(
        tasks,
        weekly_availability=weekly_availability,
        exceptions=exceptions or [],
        existing_schedule=existing_schedule or [],
        scheduling_start=scheduling_start,
        scheduling_end=scheduling_end,
        timezone_name=timezone_name,
    )


def _assert_pipeline_invariants(
    result: SchedulingResult,
    tasks: list[SchedulingTask],
    *,
    weekly_availability: list[WeeklyAvailability],
    exceptions: list[AvailabilityExceptionInput],
    existing_schedule: list[ExistingScheduleBlock],
    scheduling_start: datetime,
    scheduling_end: datetime,
    timezone_name: str,
):
    availability = generate_availability_windows(
        weekly_availability,
        exceptions,
        existing_schedule,
        scheduling_start,
        scheduling_end,
        timezone_name,
    )
    tasks_by_id = {task.task_id: task for task in tasks}
    scheduled_minutes = {task.task_id: 0 for task in tasks}
    unscheduled_minutes = {
        work.task_id: work.remaining_duration_minutes
        for work in result.unscheduled_work
    }
    occupied_intervals = []
    for occupied in existing_schedule:
        start_utc = occupied.start.astimezone(timezone.utc)
        end_utc = occupied.end.astimezone(timezone.utc)
        occupied_start = start_utc.replace(second=0, microsecond=0)
        floored_end = end_utc.replace(second=0, microsecond=0)
        occupied_end = (
            floored_end
            if end_utc == floored_end
            else floored_end + timedelta(minutes=1)
        )
        occupied_intervals.append((occupied_start, occupied_end))

    ordered_blocks = sorted(result.blocks, key=lambda block: block.start)
    for previous, current in zip(ordered_blocks, ordered_blocks[1:]):
        assert previous.end <= current.start

    for block in result.blocks:
        task = tasks_by_id[block.task_id]
        duration_minutes = int((block.end - block.start).total_seconds() // 60)
        assert scheduling_start <= block.start < block.end <= scheduling_end
        assert block.end <= task.deadline
        assert duration_minutes >= task.minimum_session_length_minutes
        assert any(
            window.start <= block.start and block.end <= window.end
            for window in availability
        )
        assert all(
            block.end <= occupied_start or occupied_end <= block.start
            for occupied_start, occupied_end in occupied_intervals
        )
        scheduled_minutes[task.task_id] += duration_minutes

    for task in tasks:
        assert (
            scheduled_minutes[task.task_id]
            + unscheduled_minutes.get(task.task_id, 0)
            == task.remaining_duration_minutes
        )


def _assert_valid(
    result,
    tasks,
    *,
    weekly_availability,
    exceptions=None,
    existing_schedule=None,
    scheduling_start,
    scheduling_end,
    timezone_name="UTC",
):
    _assert_pipeline_invariants(
        result,
        tasks,
        weekly_availability=weekly_availability,
        exceptions=exceptions or [],
        existing_schedule=existing_schedule or [],
        scheduling_start=scheduling_start,
        scheduling_end=scheduling_end,
        timezone_name=timezone_name,
    )


def test_pipeline_schedules_multiple_tasks_in_weekly_availability():
    start = _utc(2026, 9, 28)
    end = _utc(2026, 9, 29)
    tasks = [
        _task(1, priority=TaskPriority.low),
        _task(2, priority=TaskPriority.high),
    ]
    weekly = [WeeklyAvailability(0, time(9), time(11))]

    result = _schedule(
        tasks,
        weekly_availability=weekly,
        scheduling_start=start,
        scheduling_end=end,
    )

    assert [(block.task_id, block.start, block.end) for block in result.blocks] == [
        (2, _utc(2026, 9, 28, 9), _utc(2026, 9, 28, 10)),
        (1, _utc(2026, 9, 28, 10), _utc(2026, 9, 28, 11)),
    ]
    assert result.unscheduled_work == []
    _assert_valid(
        result,
        tasks,
        weekly_availability=weekly,
        scheduling_start=start,
        scheduling_end=end,
    )


def test_available_exception_replaces_weekly_availability():
    start = _utc(2026, 9, 28)
    end = _utc(2026, 9, 29)
    weekly = [WeeklyAvailability(0, time(9), time(12))]
    exceptions = [
        AvailabilityExceptionInput(
            date(2026, 9, 28), True, start_time=time(13), end_time=time(14)
        )
    ]
    tasks = [_task(1)]

    result = _schedule(
        tasks,
        weekly_availability=weekly,
        exceptions=exceptions,
        scheduling_start=start,
        scheduling_end=end,
    )

    assert [(block.start, block.end) for block in result.blocks] == [
        (_utc(2026, 9, 28, 13), _utc(2026, 9, 28, 14))
    ]
    _assert_valid(
        result,
        tasks,
        weekly_availability=weekly,
        exceptions=exceptions,
        scheduling_start=start,
        scheduling_end=end,
    )


def test_unavailable_exception_overrides_weekly_availability():
    start = _utc(2026, 9, 28)
    end = _utc(2026, 9, 29)
    weekly = [WeeklyAvailability(0, time(9), time(12))]
    exceptions = [AvailabilityExceptionInput(date(2026, 9, 28), False)]
    tasks = [_task(1)]

    result = _schedule(
        tasks,
        weekly_availability=weekly,
        exceptions=exceptions,
        scheduling_start=start,
        scheduling_end=end,
    )

    assert result.blocks == []
    assert [(item.task_id, item.remaining_duration_minutes) for item in result.unscheduled_work] == [
        (1, 60)
    ]
    _assert_valid(
        result,
        tasks,
        weekly_availability=weekly,
        exceptions=exceptions,
        scheduling_start=start,
        scheduling_end=end,
    )


def test_exception_uses_local_date_when_it_differs_from_utc_date():
    start = _utc(2026, 9, 28)
    end = _utc(2026, 9, 28, 8)
    timezone_name = "America/Los_Angeles"
    weekly = [
        WeeklyAvailability(6, time(18), time(23)),
        WeeklyAvailability(0, time(0), time(1)),
    ]
    exceptions = [AvailabilityExceptionInput(date(2026, 9, 27), False)]
    tasks = [_task(1)]

    result = _schedule(
        tasks,
        weekly_availability=weekly,
        exceptions=exceptions,
        scheduling_start=start,
        scheduling_end=end,
        timezone_name=timezone_name,
    )

    assert [(block.start, block.end) for block in result.blocks] == [
        (_utc(2026, 9, 28, 7), _utc(2026, 9, 28, 8))
    ]
    _assert_valid(
        result,
        tasks,
        weekly_availability=weekly,
        exceptions=exceptions,
        scheduling_start=start,
        scheduling_end=end,
        timezone_name=timezone_name,
    )


def test_available_exception_and_existing_block_apply_on_same_local_date():
    start = _utc(2026, 9, 28)
    end = _utc(2026, 9, 29)
    weekly = [WeeklyAvailability(0, time(13), time(17))]
    exceptions = [
        AvailabilityExceptionInput(
            date(2026, 9, 28), True, start_time=time(9), end_time=time(12)
        )
    ]
    existing = [
        ExistingScheduleBlock(
            start=_utc(2026, 9, 28, 10), end=_utc(2026, 9, 28, 11)
        )
    ]
    tasks = [_task(1, remaining_duration_minutes=120)]

    result = _schedule(
        tasks,
        weekly_availability=weekly,
        exceptions=exceptions,
        existing_schedule=existing,
        scheduling_start=start,
        scheduling_end=end,
    )

    assert [(block.start, block.end) for block in result.blocks] == [
        (_utc(2026, 9, 28, 9), _utc(2026, 9, 28, 10)),
        (_utc(2026, 9, 28, 11), _utc(2026, 9, 28, 12)),
    ]
    _assert_valid(
        result,
        tasks,
        weekly_availability=weekly,
        exceptions=exceptions,
        existing_schedule=existing,
        scheduling_start=start,
        scheduling_end=end,
    )


def test_subminute_existing_block_is_rounded_outward_in_pipeline():
    start = _utc(2026, 9, 28, 10)
    end = _utc(2026, 9, 28, 11)
    weekly = [WeeklyAvailability(0, time(10), time(11))]
    existing = [
        ExistingScheduleBlock(
            start=_utc(2026, 9, 28, 10, 15, 10),
            end=_utc(2026, 9, 28, 10, 30, 20),
        )
    ]
    tasks = [_task(1)]

    result = _schedule(
        tasks,
        weekly_availability=weekly,
        existing_schedule=existing,
        scheduling_start=start,
        scheduling_end=end,
    )

    assert [(block.start, block.end) for block in result.blocks] == [
        (_utc(2026, 9, 28, 10), _utc(2026, 9, 28, 10, 15)),
        (_utc(2026, 9, 28, 10, 31), _utc(2026, 9, 28, 11)),
    ]
    assert [
        (item.task_id, item.remaining_duration_minutes)
        for item in result.unscheduled_work
    ] == [(1, 16)]
    _assert_valid(
        result,
        tasks,
        weekly_availability=weekly,
        existing_schedule=existing,
        scheduling_start=start,
        scheduling_end=end,
    )


def test_existing_work_is_not_subtracted_twice(monkeypatch):
    start = _utc(2026, 9, 28, 9)
    end = _utc(2026, 9, 28, 10)
    weekly = [WeeklyAvailability(0, time(9), time(10))]
    existing = [
        ExistingScheduleBlock(
            start=_utc(2026, 9, 28, 15), end=_utc(2026, 9, 28, 16)
        )
    ]
    tasks = [_task(1)]
    scheduling_inputs = []
    original_schedule = pipeline.schedule

    def capture_scheduling_input(scheduling_input):
        scheduling_inputs.append(scheduling_input)
        return original_schedule(scheduling_input)

    monkeypatch.setattr(pipeline, "schedule", capture_scheduling_input)
    result = _schedule(
        tasks,
        weekly_availability=weekly,
        existing_schedule=existing,
        scheduling_start=start,
        scheduling_end=end,
    )

    assert result.unscheduled_work == []
    assert len(result.blocks) == 1
    assert scheduling_inputs[0].existing_schedule == []
    _assert_valid(
        result,
        tasks,
        weekly_availability=weekly,
        existing_schedule=existing,
        scheduling_start=start,
        scheduling_end=end,
    )


def test_deadlines_before_start_and_after_end_are_respected():
    start = _utc(2026, 9, 28, 9)
    end = _utc(2026, 9, 28, 10)
    weekly = [WeeklyAvailability(0, time(9), time(10))]
    tasks = [
        _task(1, priority=TaskPriority.high, deadline=_utc(2026, 9, 28, 8, 59)),
        _task(2, priority=TaskPriority.low, deadline=_utc(2026, 9, 28, 18)),
    ]

    result = _schedule(
        tasks,
        weekly_availability=weekly,
        scheduling_start=start,
        scheduling_end=end,
    )

    assert [(block.task_id, block.start, block.end) for block in result.blocks] == [
        (2, start, end)
    ]
    assert [
        (item.task_id, item.remaining_duration_minutes)
        for item in result.unscheduled_work
    ] == [(1, 60)]
    _assert_valid(
        result,
        tasks,
        weekly_availability=weekly,
        scheduling_start=start,
        scheduling_end=end,
    )


def test_spring_forward_gap_normalization_reaches_allocator():
    start = _utc(2026, 3, 8, 7)
    end = _utc(2026, 3, 8, 9)
    timezone_name = "America/New_York"
    weekly = [WeeklyAvailability(6, time(2, 30), time(5))]
    tasks = [_task(1)]

    result = _schedule(
        tasks,
        weekly_availability=weekly,
        scheduling_start=start,
        scheduling_end=end,
        timezone_name=timezone_name,
    )

    assert [(block.start, block.end) for block in result.blocks] == [
        (_utc(2026, 3, 8, 7, 30), _utc(2026, 3, 8, 8, 30))
    ]
    _assert_valid(
        result,
        tasks,
        weekly_availability=weekly,
        scheduling_start=start,
        scheduling_end=end,
        timezone_name=timezone_name,
    )


@pytest.mark.parametrize(
    ("scheduling_start", "scheduling_end", "error_field"),
    [
        (_utc(2026, 9, 28, 9, 0, 1), _utc(2026, 9, 28, 10), "scheduling_start"),
        (_utc(2026, 9, 28, 9), _utc(2026, 9, 28, 10, 0, 1), "scheduling_end"),
    ],
)
def test_pipeline_rejects_subminute_bounds_with_bound_name(
    scheduling_start, scheduling_end, error_field
):
    with pytest.raises(ValueError, match=error_field):
        _schedule(
            [],
            weekly_availability=[],
            scheduling_start=scheduling_start,
            scheduling_end=scheduling_end,
        )
