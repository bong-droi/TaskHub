from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["Viết tài liệu API"])
    description: str | None = Field(default=None, max_length=2000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


class TaskCreate(TaskBase):
    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("due_date không được ở quá khứ")
        return v


class TaskUpdate(BaseModel):
    """Dùng cho PATCH: mọi field đều optional."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)  # chuẩn bị cho ORM ở Ngày 2

    id: int
    status: TaskStatus
    created_at: datetime
