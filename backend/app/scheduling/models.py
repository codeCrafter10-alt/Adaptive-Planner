from datetime import datetime

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.models.task import TaskPriority


class SchedulingTask(BaseModel):
    task_id: int = Field(gt=0)
    remaining_duration_minutes: int = Field(gt=0)
    minimum_session_length_minutes: int = Field(gt=0)
    priority: TaskPriority
    deadline: AwareDatetime

    @model_validator(mode="after")
    def validate_minimum_session_length(self) -> "SchedulingTask":
        if self.minimum_session_length_minutes > self.remaining_duration_minutes:
            raise ValueError(
                "minimum_session_length_minutes must not exceed "
                "remaining_duration_minutes"
            )

        return self


class AvailabilityWindow(BaseModel):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def validate_time_range(self) -> "AvailabilityWindow":
        _validate_time_range(self.start, self.end)
        return self


class ExistingScheduleBlock(BaseModel):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def validate_time_range(self) -> "ExistingScheduleBlock":
        _validate_time_range(self.start, self.end)
        return self


class ScheduleBlock(BaseModel):
    task_id: int = Field(gt=0)
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def validate_time_range(self) -> "ScheduleBlock":
        _validate_time_range(self.start, self.end)
        return self


class UnscheduledWork(BaseModel):
    task_id: int = Field(gt=0)
    remaining_duration_minutes: int = Field(gt=0)


class SchedulingInput(BaseModel):
    tasks: list[SchedulingTask]
    availability: list[AvailabilityWindow]
    existing_schedule: list[ExistingScheduleBlock]
    scheduling_start: AwareDatetime
    scheduling_end: AwareDatetime

    @model_validator(mode="after")
    def validate_scheduling_range(self) -> "SchedulingInput":
        _validate_time_range(self.scheduling_start, self.scheduling_end)
        return self


class SchedulingResult(BaseModel):
    blocks: list[ScheduleBlock]
    unscheduled_work: list[UnscheduledWork]


def _validate_time_range(start: datetime, end: datetime) -> None:
    if start >= end:
        raise ValueError("start must be before end")
