from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.messages import DUE_DATE_IN_PAST, FIELD_CANNOT_BE_NULL
from app.schemas.enums import TaskPriority, TaskStatus


def _validate_due_date(v: date | None) -> date | None:
    if v is not None and v < date.today():
        raise ValueError(DUE_DATE_IN_PAST)
    return v


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["Viết tài liệu API"])
    description: str | None = Field(default=None, max_length=2000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


class TaskCreate(TaskBase):
    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v: date | None) -> date | None:
        return _validate_due_date(v)

    @field_validator("title", "description", mode="before")
    @classmethod
    def required_fields_cannot_be_null(cls, v: object) -> object:
        if v is None:
            raise ValueError(FIELD_CANNOT_BE_NULL)
        return v


class TaskUpdate(BaseModel):
    """Dùng cho PATCH: mỗi field đều optional."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v: date | None) -> date | None:
        return _validate_due_date(v)


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)  # chuẩn bị cho ORM ở Ngày 2

    id: int
    status: TaskStatus
    created_at: datetime
