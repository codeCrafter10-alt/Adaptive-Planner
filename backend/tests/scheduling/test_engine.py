from datetime import datetime, timezone

from app.models.task import TaskPriority
from app.scheduling.engine import schedule
from app.scheduling.models import (
    AvailabilityWindow,
    ExistingScheduleBlock,
    SchedulingInput,
    SchedulingTask,
)


START = datetime(2026, 9, 25, 9, 0, tzinfo=timezone.utc)
END = datetime(2026, 9, 25, 17, 0, tzinfo=timezone.utc)


def _task(task_id=1, **overrides):
    values = {
        "task_id": task_id,
        "remaining_duration_minutes": 60,
        "minimum_session_length_minutes": 15,
        "priority": TaskPriority.medium,
        "deadline": END,
    }
    values.update(overrides)
    return SchedulingTask(**values)


def _input(tasks, availability, existing_schedule=None, end=END):
    return SchedulingInput(
        tasks=tasks,
        availability=availability,
        existing_schedule=existing_schedule or [],
        scheduling_start=START,
        scheduling_end=end,
    )


def test_schedule_allocates_work_in_chronological_windows():
    result = schedule(
        _input(
            [_task(remaining_duration_minutes=90)],
            [
                AvailabilityWindow(
                    start=datetime(2026, 9, 25, 13, tzinfo=timezone.utc),
                    end=datetime(2026, 9, 25, 14, tzinfo=timezone.utc),
                ),
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                ),
            ],
        )
    )

    assert [(block.start, block.end) for block in result.blocks] == [
        (START, datetime(2026, 9, 25, 10, tzinfo=timezone.utc)),
        (
            datetime(2026, 9, 25, 13, tzinfo=timezone.utc),
            datetime(2026, 9, 25, 13, 30, tzinfo=timezone.utc),
        ),
    ]
    assert result.unscheduled_work == []


def test_priority_takes_precedence_over_earlier_deadline():
    result = schedule(
        _input(
            [
                _task(
                    task_id=1,
                    priority=TaskPriority.low,
                    deadline=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                ),
                _task(task_id=2, priority=TaskPriority.high),
            ],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                )
            ],
        )
    )

    assert [block.task_id for block in result.blocks] == [2]
    assert [(item.task_id, item.remaining_duration_minutes) for item in result.unscheduled_work] == [
        (1, 60)
    ]


def test_deadline_then_task_id_breaks_equal_priority_ties():
    result = schedule(
        _input(
            [
                _task(
                    task_id=3,
                    deadline=datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                ),
                _task(
                    task_id=2,
                    deadline=datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                ),
                _task(
                    task_id=1,
                    deadline=datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                ),
            ],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                )
            ],
        )
    )

    assert [block.task_id for block in result.blocks] == [1]
    assert [item.task_id for item in result.unscheduled_work] == [2, 3]


def test_deadline_is_hard_and_end_is_exclusive():
    deadline = datetime(2026, 9, 25, 10, tzinfo=timezone.utc)
    result = schedule(
        _input(
            [_task(remaining_duration_minutes=90, deadline=deadline)],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 11, tzinfo=timezone.utc),
                ),
                AvailabilityWindow(start=deadline, end=END),
            ],
        )
    )

    assert result.blocks[0].start == START
    assert result.blocks[0].end == deadline
    assert result.unscheduled_work[0].remaining_duration_minutes == 30


def test_allocations_are_clipped_to_scheduling_bounds():
    result = schedule(
        _input(
            [_task(remaining_duration_minutes=90)],
            [
                AvailabilityWindow(
                    start=datetime(2026, 9, 25, 8, tzinfo=timezone.utc),
                    end=datetime(2026, 9, 25, 18, tzinfo=timezone.utc),
                )
            ],
        )
    )

    assert len(result.blocks) == 1
    assert result.blocks[0].task_id == 1
    assert result.blocks[0].start == START
    assert result.blocks[0].end == datetime(
        2026, 9, 25, 10, 30, tzinfo=timezone.utc
    )


def test_task_at_scheduling_start_or_after_has_no_eligible_time():
    result = schedule(
        _input(
            [
                _task(
                    task_id=1,
                    deadline=START,
                ),
                _task(
                    task_id=2,
                    deadline=datetime(2026, 9, 25, 8, 59, tzinfo=timezone.utc),
                ),
            ],
            [AvailabilityWindow(start=START, end=END)],
        )
    )

    assert result.blocks == []
    assert [(item.task_id, item.remaining_duration_minutes) for item in result.unscheduled_work] == [
        (2, 60),
        (1, 60),
    ]


def test_allocation_does_not_strand_sub_minimum_residual_work():
    result = schedule(
        _input(
            [
                _task(
                    remaining_duration_minutes=40,
                    minimum_session_length_minutes=30,
                )
            ],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 9, 35, tzinfo=timezone.utc),
                ),
                AvailabilityWindow(
                    start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                    end=datetime(2026, 9, 25, 10, 35, tzinfo=timezone.utc),
                ),
            ],
        )
    )

    assert result.blocks == []
    assert result.unscheduled_work[0].remaining_duration_minutes == 40


def test_sub_minimum_remainder_stays_unscheduled_when_next_window_is_too_short():
    result = schedule(
        _input(
            [
                _task(
                    remaining_duration_minutes=65,
                    minimum_session_length_minutes=30,
                )
            ],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 9, 35, tzinfo=timezone.utc),
                ),
                AvailabilityWindow(
                    start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                    end=datetime(2026, 9, 25, 10, 20, tzinfo=timezone.utc),
                ),
            ],
        )
    )

    assert len(result.blocks) == 1
    assert result.blocks[0].task_id == 1
    assert result.blocks[0].start == START
    assert result.blocks[0].end == datetime(
        2026, 9, 25, 9, 35, tzinfo=timezone.utc
    )
    assert result.unscheduled_work[0].remaining_duration_minutes == 30


def test_fifty_minute_window_trims_allocation_to_preserve_minimum_remainder():
    result = schedule(
        _input(
            [
                _task(
                    remaining_duration_minutes=65,
                    minimum_session_length_minutes=30,
                )
            ],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 9, 50, tzinfo=timezone.utc),
                )
            ],
        )
    )

    assert len(result.blocks) == 1
    assert result.blocks[0].start == START
    assert result.blocks[0].end == datetime(
        2026, 9, 25, 9, 35, tzinfo=timezone.utc
    )
    assert result.unscheduled_work[0].remaining_duration_minutes == 30


def test_allocation_trims_to_preserve_minimum_final_session():
    result = schedule(
        _input(
            [
                _task(
                    remaining_duration_minutes=65,
                    minimum_session_length_minutes=30,
                )
            ],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 9, 50, tzinfo=timezone.utc),
                ),
                AvailabilityWindow(
                    start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                    end=datetime(2026, 9, 25, 11, tzinfo=timezone.utc),
                ),
            ],
        )
    )

    assert [
        (block.start, block.end) for block in result.blocks
    ] == [
        (
            START,
            datetime(2026, 9, 25, 9, 35, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc),
        ),
    ]
    assert result.unscheduled_work == []


def test_task_can_continue_across_multiple_windows_without_short_blocks():
    result = schedule(
        _input(
            [_task(remaining_duration_minutes=75, minimum_session_length_minutes=30)],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 9, 30, tzinfo=timezone.utc),
                ),
                AvailabilityWindow(
                    start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                    end=datetime(2026, 9, 25, 10, 45, tzinfo=timezone.utc),
                ),
            ],
        )
    )

    assert [
        (block.start, block.end) for block in result.blocks
    ] == [
        (
            START,
            datetime(2026, 9, 25, 9, 30, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            datetime(2026, 9, 25, 10, 45, tzinfo=timezone.utc),
        ),
    ]
    assert result.unscheduled_work == []


def test_existing_schedule_is_already_removed_from_phase_7_2_windows():
    existing = ExistingScheduleBlock(
        start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
        end=datetime(2026, 9, 25, 11, tzinfo=timezone.utc),
    )
    result = schedule(
        _input(
            [_task(remaining_duration_minutes=60)],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                )
            ],
            existing_schedule=[existing],
        )
    )

    assert result.blocks[0].end == datetime(2026, 9, 25, 10, tzinfo=timezone.utc)
    assert result.unscheduled_work == []


def test_two_tasks_sharing_one_window_cannot_overlap():
    result = schedule(
        _input(
            [
                _task(task_id=1, priority=TaskPriority.high),
                _task(task_id=2, priority=TaskPriority.medium),
            ],
            [AvailabilityWindow(start=START, end=datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc))],
        )
    )

    assert [
        (block.task_id, block.start, block.end) for block in result.blocks
    ] == [
        (
            1,
            START,
            datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
        ),
        (
            2,
            datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc),
        ),
    ]
    assert len(result.unscheduled_work) == 1
    assert result.unscheduled_work[0].task_id == 2
    assert result.unscheduled_work[0].remaining_duration_minutes == 30


def test_schedule_is_deterministic_for_shuffled_input_and_does_not_mutate_it():
    tasks = [
        _task(task_id=2, priority=TaskPriority.high),
        _task(task_id=1, priority=TaskPriority.high),
    ]
    availability = [
        AvailabilityWindow(
            start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            end=datetime(2026, 9, 25, 11, tzinfo=timezone.utc),
        ),
        AvailabilityWindow(start=START, end=datetime(2026, 9, 25, 10, tzinfo=timezone.utc)),
    ]
    original_tasks = tasks[:]
    original_availability = availability[:]

    first = schedule(_input(tasks, availability))
    second = schedule(_input(list(reversed(tasks)), list(reversed(availability))))

    assert first == second
    assert tasks == original_tasks
    assert availability == original_availability


def test_empty_input_returns_empty_result():
    result = schedule(_input([], []))

    assert result.blocks == []
    assert result.unscheduled_work == []
