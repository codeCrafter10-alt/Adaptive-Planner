from datetime import time, datetime

from pydantic import BaseModel, Field, ConfigDict, model_validator

class AvailabilityBase(BaseModel):
    """
    Base schema for availability blocks.
    """

    day_of_week: int = Field(
        ...,
        ge=0,
        le=6,
        description="0 = Monday ... 6 = Sunday",
    )

    start_time: time
    end_time: time

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")

        return self


class AvailabilityCreate(AvailabilityBase):
    pass


class AvailabilityUpdate(AvailabilityBase):
    pass


class AvailabilityResponse(BaseModel):
    """
    Response schema for availability blocks.
    """

    id: int
    day_of_week: int
    start_time: time
    end_time: time
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
