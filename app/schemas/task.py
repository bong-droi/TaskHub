from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TaskPriority, TaskStatus

__all__ = ["TaskCreate", "TaskPriority", "TaskRead", "TaskStatus", "TaskUpdate"]


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["Viết tài liệu API"])
    description: str | None = Field(default=None, max_length=2000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


class TaskCreate(TaskBase):
    project_id: int = Field(gt=0)
    assignee_id: int | None = Field(default=None, gt=0)

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
    assignee_id: int | None = Field(default=None, gt=0)


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)  # đọc thẳng từ ORM object

    id: int
    project_id: int
    assignee_id: int | None
    created_by: int | None
    status: TaskStatus
    created_at: datetime
