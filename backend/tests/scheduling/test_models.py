from datetime import datetime, timezone

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


def test_priority_reuses_existing_task_priority():
    task = _task(priority=TaskPriority.high)

    assert task.priority is TaskPriority.high

    with pytest.raises(ValidationError):
        _task(priority="urgent")
