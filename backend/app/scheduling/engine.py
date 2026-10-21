from datetime import timedelta

from app.models.task import TaskPriority
from app.scheduling.models import (
    ScheduleBlock,
    SchedulingInput,
    SchedulingResult,
    UnscheduledWork,
)


_PRIORITY_ORDER = {
    TaskPriority.high: 0,
    TaskPriority.medium: 1,
    TaskPriority.low: 2,
}


def schedule(input: SchedulingInput) -> SchedulingResult:
    """Greedily allocate tasks into disjoint free availability windows.

    Availability windows are assumed to be disjoint because they are produced
    by the Phase 7.2 generator, which subtracts and normalizes existing work.
    """
    remaining_windows = sorted(
        (window.start, window.end) for window in input.availability
    )
    ordered_tasks = sorted(
        input.tasks,
        key=lambda task: (
            _PRIORITY_ORDER[task.priority],
            task.deadline,
            task.task_id,
        ),
    )

    blocks: list[ScheduleBlock] = []
    unscheduled_work: list[UnscheduledWork] = []

    for task in ordered_tasks:
        remaining_minutes = task.remaining_duration_minutes
        if task.deadline > input.scheduling_start:
            for index, (window_start, window_end) in enumerate(remaining_windows):
                if remaining_minutes == 0:
                    break
                if window_start >= task.deadline:
                    break

                candidate_start = max(window_start, input.scheduling_start)
                candidate_end = min(
                    window_end,
                    input.scheduling_end,
                    task.deadline,
                )
                if candidate_start >= candidate_end:
                    continue

                available_minutes = int(
                    (candidate_end - candidate_start).total_seconds() // 60
                )
                if available_minutes < task.minimum_session_length_minutes:
                    continue

                allocated_minutes = min(remaining_minutes, available_minutes)
                residual_minutes = remaining_minutes - allocated_minutes
                if 0 < residual_minutes < task.minimum_session_length_minutes:
                    allocated_minutes = (
                        remaining_minutes - task.minimum_session_length_minutes
                    )
                    if allocated_minutes < task.minimum_session_length_minutes:
                        continue

                block_end = candidate_start + timedelta(minutes=allocated_minutes)
                blocks.append(
                    ScheduleBlock(
                        task_id=task.task_id,
                        start=candidate_start,
                        end=block_end,
                    )
                )
                remaining_minutes -= allocated_minutes
                remaining_windows[index] = (block_end, window_end)

        if remaining_minutes > 0:
            unscheduled_work.append(
                UnscheduledWork(
                    task_id=task.task_id,
                    remaining_duration_minutes=remaining_minutes,
                )
            )

    return SchedulingResult(blocks=blocks, unscheduled_work=unscheduled_work)
