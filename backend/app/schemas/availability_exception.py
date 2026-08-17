from __future__ import annotations
from datetime import date as date_type, datetime, time
from pydantic import BaseModel, ConfigDict, model_validator


class AvailabilityExceptionBase(BaseModel):
    """Base schema for date-specific availability exceptions."""

    date: date_type
    is_available: bool
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.is_available:
            if self.start_time is None or self.end_time is None:
                raise ValueError("start_time and end_time must both be provided when is_available is true.")
        else:
            if self.start_time is not None or self.end_time is not None:
                raise ValueError("start_time and end_time must be null when is_available is false.")

        if self.start_time is not None and self.end_time is not None and self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time.")

        return self


class AvailabilityExceptionCreate(AvailabilityExceptionBase):
    pass


class AvailabilityExceptionUpdate(BaseModel):
    date: date_type | None = None
    is_available: bool | None = None
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if "start_time" in self.model_fields_set or "end_time" in self.model_fields_set:
            if (self.start_time is None) != (self.end_time is None):
                raise ValueError(
                    "start_time and end_time must both be provided or both be null."
                )

            if (
                self.start_time is not None
                and self.end_time is not None
                and self.start_time >= self.end_time
            ):
                raise ValueError("start_time must be before end_time.")

        return self


class AvailabilityExceptionResponse(AvailabilityExceptionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
