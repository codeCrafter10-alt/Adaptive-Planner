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


def _assert_valid_result(result, tasks, availability, end=END):
    task_by_id = {task.task_id: task for task in tasks}
    scheduled_minutes = {task.task_id: 0 for task in tasks}
    unscheduled_minutes = {
        item.task_id: item.remaining_duration_minutes
        for item in result.unscheduled_work
    }
    ordered_blocks = sorted(result.blocks, key=lambda block: block.start)
    availability_union = []
    for window in sorted(availability, key=lambda item: (item.start, item.end)):
        if availability_union and window.start <= availability_union[-1][1]:
            availability_union[-1] = (
                availability_union[-1][0],
                max(availability_union[-1][1], window.end),
            )
        else:
            availability_union.append((window.start, window.end))

    for previous, current in zip(ordered_blocks, ordered_blocks[1:]):
        assert previous.end <= current.start

    for block in result.blocks:
        task = task_by_id[block.task_id]
        duration = int((block.end - block.start).total_seconds() // 60)
        assert START <= block.start < block.end <= end
        assert block.end <= task.deadline
        assert duration >= task.minimum_session_length_minutes
        assert any(
            window_start <= block.start and block.end <= window_end
            for window_start, window_end in availability_union
        )
        scheduled_minutes[task.task_id] += duration

    for task in tasks:
        assert (
            scheduled_minutes[task.task_id] + unscheduled_minutes.get(task.task_id, 0)
            == task.remaining_duration_minutes
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
                    end=deadline,
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


def test_sub_minimum_remainder_is_intentionally_left_unscheduled():
    task = _task(remaining_duration_minutes=40, minimum_session_length_minutes=30)
    availability = [
        AvailabilityWindow(
            start=START,
            end=datetime(2026, 9, 25, 9, 35, tzinfo=timezone.utc),
        ),
        AvailabilityWindow(
            start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            end=datetime(2026, 9, 25, 10, 35, tzinfo=timezone.utc),
        ),
    ]
    result = schedule(
        _input([task], availability)
    )

    assert [(block.start, block.end) for block in result.blocks] == [
        (
            START,
            datetime(2026, 9, 25, 9, 35, tzinfo=timezone.utc),
        )
    ]
    assert result.unscheduled_work[0].remaining_duration_minutes == 5
    _assert_valid_result(result, [task], availability)


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


def test_fifty_minute_window_leaves_sub_minimum_remainder_unscheduled():
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
        2026, 9, 25, 9, 50, tzinfo=timezone.utc
    )
    assert result.unscheduled_work[0].remaining_duration_minutes == 15


def test_fifty_plus_twenty_window_schedules_fifty_and_improves_over_old_trim():
    task = _task(
        remaining_duration_minutes=65,
        minimum_session_length_minutes=30,
    )
    availability = [
        AvailabilityWindow(
            start=START,
            end=datetime(2026, 9, 25, 9, 50, tzinfo=timezone.utc),
        ),
        AvailabilityWindow(
            start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            end=datetime(2026, 9, 25, 10, 20, tzinfo=timezone.utc),
        ),
    ]

    result = schedule(_input([task], availability))
    scheduled_minutes = sum(
        int((block.end - block.start).total_seconds() // 60)
        for block in result.blocks
    )

    assert scheduled_minutes == 50
    assert scheduled_minutes > 35
    assert result.unscheduled_work[0].remaining_duration_minutes == 15
    _assert_valid_result(result, [task], availability)


def test_allocation_trims_to_preserve_minimum_final_session():
    task = _task(
        remaining_duration_minutes=65,
        minimum_session_length_minutes=30,
    )
    availability = [
        AvailabilityWindow(
            start=START,
            end=datetime(2026, 9, 25, 9, 50, tzinfo=timezone.utc),
        ),
        AvailabilityWindow(
            start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            end=datetime(2026, 9, 25, 11, tzinfo=timezone.utc),
        ),
    ]
    result = schedule(
        _input([task], availability)
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
    _assert_valid_result(result, [task], availability)


def test_trim_lookahead_is_deterministic_for_shuffled_inputs():
    tasks = [
        _task(
            task_id=1,
            priority=TaskPriority.high,
            remaining_duration_minutes=65,
            minimum_session_length_minutes=30,
        ),
        _task(
            task_id=2,
            priority=TaskPriority.low,
            remaining_duration_minutes=30,
            minimum_session_length_minutes=30,
        ),
    ]
    availability = [
        AvailabilityWindow(
            start=START,
            end=datetime(2026, 9, 25, 9, 50, tzinfo=timezone.utc),
        ),
        AvailabilityWindow(
            start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            end=datetime(2026, 9, 25, 11, 30, tzinfo=timezone.utc),
        ),
    ]

    baseline = schedule(_input(tasks, availability))
    reversed_tasks = schedule(_input(list(reversed(tasks)), availability))
    reversed_windows = schedule(_input(tasks, list(reversed(availability))))
    both_reversed = schedule(
        _input(list(reversed(tasks)), list(reversed(availability)))
    )

    assert baseline == reversed_tasks == reversed_windows == both_reversed
    _assert_valid_result(baseline, tasks, availability)


def test_deadline_clipped_lookahead_does_not_trim_without_a_usable_later_window():
    task = _task(
        remaining_duration_minutes=65,
        minimum_session_length_minutes=30,
        deadline=datetime(2026, 9, 25, 10, 20, tzinfo=timezone.utc),
    )
    availability = [
        AvailabilityWindow(
            start=START,
            end=datetime(2026, 9, 25, 9, 50, tzinfo=timezone.utc),
        ),
        AvailabilityWindow(
            start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            end=END,
        ),
    ]

    result = schedule(_input([task], availability))

    assert [(block.start, block.end) for block in result.blocks] == [
        (
            START,
            datetime(2026, 9, 25, 9, 50, tzinfo=timezone.utc),
        )
    ]
    assert result.unscheduled_work[0].remaining_duration_minutes == 15
    _assert_valid_result(result, [task], availability)


def test_task_stops_when_remaining_work_is_below_minimum():
    task = _task(remaining_duration_minutes=4, minimum_session_length_minutes=3)
    availability = [
        AvailabilityWindow(
            start=START,
            end=datetime(2026, 9, 25, 9, 3, tzinfo=timezone.utc),
        ),
        AvailabilityWindow(
            start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            end=datetime(2026, 9, 25, 10, 3, tzinfo=timezone.utc),
        ),
    ]

    result = schedule(_input([task], availability))

    assert [(block.start, block.end) for block in result.blocks] == [
        (
            START,
            datetime(2026, 9, 25, 9, 3, tzinfo=timezone.utc),
        )
    ]
    assert result.unscheduled_work[0].remaining_duration_minutes == 1
    _assert_valid_result(result, [task], availability)


def test_priority_order_can_leave_more_total_work_unscheduled():
    high_priority = _task(
        task_id=1,
        remaining_duration_minutes=5,
        minimum_session_length_minutes=3,
        priority=TaskPriority.high,
    )
    constrained_low_priority = _task(
        task_id=2,
        remaining_duration_minutes=3,
        minimum_session_length_minutes=3,
        priority=TaskPriority.low,
        deadline=datetime(2026, 9, 25, 9, 3, tzinfo=timezone.utc),
    )
    availability = [
        AvailabilityWindow(
            start=START,
            end=datetime(2026, 9, 25, 9, 3, tzinfo=timezone.utc),
        ),
        AvailabilityWindow(
            start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            end=datetime(2026, 9, 25, 10, 3, tzinfo=timezone.utc),
        ),
    ]

    result = schedule(_input([constrained_low_priority, high_priority], availability))

    assert [(block.task_id, block.start, block.end) for block in result.blocks] == [
        (
            high_priority.task_id,
            START,
            datetime(2026, 9, 25, 9, 3, tzinfo=timezone.utc),
        )
    ]
    assert [
        (item.task_id, item.remaining_duration_minutes)
        for item in result.unscheduled_work
    ] == [(high_priority.task_id, 2), (constrained_low_priority.task_id, 3)]
    _assert_valid_result(
        result,
        [constrained_low_priority, high_priority],
        availability,
    )


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


def test_adjacent_windows_are_coalesced_for_minimum_session():
    result = schedule(
        _input(
            [
                _task(
                    remaining_duration_minutes=240,
                    minimum_session_length_minutes=240,
                )
            ],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                ),
                AvailabilityWindow(
                    start=datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
                    end=datetime(2026, 9, 25, 15, tzinfo=timezone.utc),
                ),
            ],
        )
    )

    assert [(block.start, block.end) for block in result.blocks] == [
        (START, datetime(2026, 9, 25, 13, tzinfo=timezone.utc))
    ]
    assert result.unscheduled_work == []


def test_blocks_are_sorted_chronologically_not_by_task_priority():
    result = schedule(
        _input(
            [
                _task(
                    task_id=1,
                    priority=TaskPriority.high,
                    remaining_duration_minutes=60,
                    minimum_session_length_minutes=60,
                ),
                _task(
                    task_id=2,
                    priority=TaskPriority.low,
                    remaining_duration_minutes=30,
                    minimum_session_length_minutes=30,
                ),
            ],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 9, 30, tzinfo=timezone.utc),
                ),
                AvailabilityWindow(
                    start=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                    end=datetime(2026, 9, 25, 11, tzinfo=timezone.utc),
                ),
            ],
        )
    )

    assert [block.task_id for block in result.blocks] == [2, 1]


def test_deadline_clipped_window_tail_is_reused_by_later_task():
    result = schedule(
        _input(
            [
                _task(
                    task_id=1,
                    priority=TaskPriority.high,
                    remaining_duration_minutes=90,
                    deadline=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
                ),
                _task(
                    task_id=2,
                    priority=TaskPriority.low,
                    remaining_duration_minutes=30,
                    deadline=END,
                ),
            ],
            [
                AvailabilityWindow(
                    start=START,
                    end=datetime(2026, 9, 25, 11, tzinfo=timezone.utc)
                )
            ],
        )
    )

    assert [(block.task_id, block.start, block.end) for block in result.blocks] == [
        (1, START, datetime(2026, 9, 25, 10, tzinfo=timezone.utc)),
        (
            2,
            datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
            datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc),
        ),
    ]
    assert result.unscheduled_work[0].remaining_duration_minutes == 30


def test_deadline_after_scheduling_end_does_not_extend_allocation():
    result = schedule(
        _input(
            [
                _task(
                    remaining_duration_minutes=90,
                    deadline=datetime(2026, 9, 25, 23, 59, 59, tzinfo=timezone.utc),
                )
            ],
            [AvailabilityWindow(start=START, end=END)],
            end=datetime(2026, 9, 25, 10, tzinfo=timezone.utc),
        )
    )

    assert result.blocks[0].end == datetime(2026, 9, 25, 10, tzinfo=timezone.utc)
    assert result.unscheduled_work[0].remaining_duration_minutes == 30


def test_unscheduled_work_follows_task_processing_order():
    result = schedule(
        _input(
            [
                _task(
                    task_id=2,
                    priority=TaskPriority.high,
                    deadline=datetime(2026, 9, 25, 8, 59, tzinfo=timezone.utc),
                ),
                _task(
                    task_id=1,
                    priority=TaskPriority.low,
                    deadline=datetime(2026, 9, 25, 8, 58, tzinfo=timezone.utc),
                ),
            ],
            [],
        )
    )

    assert [item.task_id for item in result.unscheduled_work] == [2, 1]
