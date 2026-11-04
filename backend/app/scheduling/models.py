from datetime import datetime, timezone

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from app.models.task import TaskPriority


class SchedulingTask(BaseModel):
    task_id: int = Field(gt=0)
    remaining_duration_minutes: int = Field(gt=0)
    minimum_session_length_minutes: int = Field(gt=0)
    priority: TaskPriority
    deadline: AwareDatetime

    @field_validator("deadline", mode="after")
    @classmethod
    def normalize_deadline(cls, value: datetime) -> datetime:
        return _as_utc(value)

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

    @field_validator("start", "end", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        value = _as_utc(value)
        _validate_whole_minute(value, "availability window")
        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> "AvailabilityWindow":
        _validate_time_range(self.start, self.end)
        return self


class ExistingScheduleBlock(BaseModel):
    start: AwareDatetime
    end: AwareDatetime

    @field_validator("start", "end", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @model_validator(mode="after")
    def validate_time_range(self) -> "ExistingScheduleBlock":
        _validate_time_range(self.start, self.end)
        return self


class ScheduleBlock(BaseModel):
    task_id: int = Field(gt=0)
    start: AwareDatetime
    end: AwareDatetime

    @field_validator("start", "end", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        return _as_utc(value)

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

    @field_validator("scheduling_start", "scheduling_end", mode="after")
    @classmethod
    def normalize_scheduling_bound(cls, value: datetime) -> datetime:
        value = _as_utc(value)
        _validate_whole_minute(value, "scheduling bounds")
        return value

    @model_validator(mode="after")
    def validate_scheduling_range(self) -> "SchedulingInput":
        _validate_time_range(self.scheduling_start, self.scheduling_end)
        task_ids = [task.task_id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("task_id values must be unique")

        windows = sorted(self.availability, key=lambda window: (window.start, window.end))
        for previous, current in zip(windows, windows[1:]):
            if current.start < previous.end:
                raise ValueError("availability windows must not overlap")
        return self


class SchedulingResult(BaseModel):
    blocks: list[ScheduleBlock]
    unscheduled_work: list[UnscheduledWork]


def _validate_time_range(start: datetime, end: datetime) -> None:
    if start >= end:
        raise ValueError("start must be before end")


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def _validate_whole_minute(value: datetime, field_name: str) -> None:
    if value.second or value.microsecond:
        raise ValueError(f"{field_name} must be aligned to whole minutes")
