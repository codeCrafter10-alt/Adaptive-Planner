from datetime import datetime

from app.scheduling.availability import (
    AvailabilityExceptionInput,
    WeeklyAvailability,
    generate_availability_windows,
)
from app.scheduling.engine import schedule
from app.scheduling.models import (
    ExistingScheduleBlock,
    SchedulingInput,
    SchedulingResult,
    SchedulingTask,
)


def schedule_with_availability(
    tasks: list[SchedulingTask],
    *,
    weekly_availability: list[WeeklyAvailability],
    exceptions: list[AvailabilityExceptionInput],
    existing_schedule: list[ExistingScheduleBlock],
    scheduling_start: datetime,
    scheduling_end: datetime,
    timezone_name: str,
) -> SchedulingResult:
    availability = generate_availability_windows(
        weekly_availability=weekly_availability,
        exceptions=exceptions,
        existing_schedule=existing_schedule,
        scheduling_start=scheduling_start,
        scheduling_end=scheduling_end,
        timezone_name=timezone_name,
    )
    scheduling_input = SchedulingInput(
        tasks=tasks,
        availability=availability,
        # Availability already excludes existing work; do not subtract it again.
        existing_schedule=[],
        scheduling_start=scheduling_start,
        scheduling_end=scheduling_end,
    )
    return schedule(scheduling_input)
