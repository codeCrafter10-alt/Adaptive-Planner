from datetime import datetime, timedelta

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
    """
    Greedily allocate tasks into coalesced free availability windows.

    All datetime values in the result are UTC-normalized. Every emitted block
    meets the task's minimum session length; a remaining sub-minimum amount is
    left unscheduled for a future adapter to handle.

    This remains an earliest-fit allocator: a different placement can
    sometimes improve global utilization, but avoiding that limitation would
    require backtracking or global optimization.
    """
    remaining_windows: list[tuple[datetime, datetime]] = []
    for window in sorted(input.availability, key=lambda item: (item.start, item.end)):
        if remaining_windows and window.start == remaining_windows[-1][1]:
            remaining_windows[-1] = (remaining_windows[-1][0], window.end)
        else:
            remaining_windows.append((window.start, window.end))
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
                if remaining_minutes < task.minimum_session_length_minutes:
                    break
                if window_start >= task.deadline:
                    break

                candidate = _clipped_candidate(
                    window_start,
                    window_end,
                    input.scheduling_start,
                    input.scheduling_end,
                    task.deadline,
                )
                if candidate is None:
                    continue
                candidate_start, candidate_end, available_minutes = candidate

                if available_minutes < task.minimum_session_length_minutes:
                    continue

                allocated_minutes = min(remaining_minutes, available_minutes)
                residual_minutes = remaining_minutes - allocated_minutes
                if 0 < residual_minutes < task.minimum_session_length_minutes:
                    trimmed_minutes = (
                        remaining_minutes - task.minimum_session_length_minutes
                    )
                    later_window_can_fit_remainder = _later_window_can_fit(
                        remaining_windows[index + 1 :],
                        input.scheduling_start,
                        input.scheduling_end,
                        task.deadline,
                        task.minimum_session_length_minutes,
                    )
                    if (
                        trimmed_minutes >= task.minimum_session_length_minutes
                        and later_window_can_fit_remainder
                    ):
                        allocated_minutes = trimmed_minutes

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

    blocks.sort(key=lambda block: (block.start, block.end, block.task_id))
    return SchedulingResult(blocks=blocks, unscheduled_work=unscheduled_work)


def _clipped_candidate(
    window_start: datetime,
    window_end: datetime,
    scheduling_start: datetime,
    scheduling_end: datetime,
    deadline: datetime,
) -> tuple[datetime, datetime, int] | None:
    candidate_start = max(window_start, scheduling_start)
    candidate_end = min(window_end, scheduling_end, deadline)
    if candidate_start >= candidate_end:
        return None

    available_minutes = int(
        (candidate_end - candidate_start).total_seconds() // 60
    )
    return candidate_start, candidate_end, available_minutes


def _later_window_can_fit(
    windows: list[tuple[datetime, datetime]],
    scheduling_start: datetime,
    scheduling_end: datetime,
    deadline: datetime,
    minimum_session_length_minutes: int,
) -> bool:
    for window_start, window_end in windows:
        candidate = _clipped_candidate(
            window_start,
            window_end,
            scheduling_start,
            scheduling_end,
            deadline,
        )
        if candidate is not None and candidate[2] >= minimum_session_length_minutes:
            return True
    return False
