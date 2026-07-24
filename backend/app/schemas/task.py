from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.task import TaskPriority


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    estimated_duration_minutes: int = Field(gt=0)
    due_date: datetime
    priority: TaskPriority = TaskPriority.medium


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    estimated_duration_minutes: int | None = Field(default=None, gt=0)
    due_date: datetime | None = None
    priority: TaskPriority | None = None
    completed: bool | None = None

    @model_validator(mode="after")
    def validate_required_fields_not_null(self):
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title cannot be null")

        if (
            "estimated_duration_minutes" in self.model_fields_set
            and self.estimated_duration_minutes is None
        ):
            raise ValueError("estimated_duration_minutes cannot be null")

        if "due_date" in self.model_fields_set and self.due_date is None:
            raise ValueError("due_date cannot be null")

        if "priority" in self.model_fields_set and self.priority is None:
            raise ValueError("priority cannot be null")

        if "completed" in self.model_fields_set and self.completed is None:
            raise ValueError("completed cannot be null")

        return self


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime