from datetime import date, datetime

from pydantic import ConfigDict, Field, field_validator

from app.core.constants import (
    DESCRIPTION_MAX_LENGTH,
    DUE_DATE_IN_PAST,
    TITLE_MAX_LENGTH,
    TITLE_MIN_LENGTH,
)
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.base import BaseSchema, not_nullable
from app.schemas.label import LabelRead
from app.schemas.types import DbId

__all__ = [
    "TaskCreate",
    "TaskCreateInProject",
    "TaskPriority",
    "TaskRead",
    "TaskStatus",
    "TaskUpdate",
]


def _validate_due_date_not_in_past(v: date | None) -> date | None:
    if v is not None and v < date.today():
        raise ValueError(DUE_DATE_IN_PAST)
    return v


class TaskBase(BaseSchema):
    title: str = Field(
        min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH, examples=["Viết tài liệu API"]
    )
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


class TaskCreateInProject(TaskBase):
    """Body của POST /projects/{id}/tasks: project_id lấy từ URL, không nhận từ body.

    Không đặt validator `due_date` vào TaskBase vì TaskRead cũng kế thừa: task cũ có due_date
    đã qua vẫn phải đọc được."""

    assignee_id: DbId | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v: date | None) -> date | None:
        return _validate_due_date_not_in_past(v)


class TaskCreate(TaskCreateInProject):
    """Body của POST /tasks (cách cũ): project_id nằm trong body."""

    project_id: DbId


class TaskUpdate(BaseSchema):
    """Dùng cho PATCH. Field vắng mặt = giữ nguyên.

    `exclude_unset=True` chỉ loại field client KHÔNG gửi, không loại `null` client gửi tường
    minh. Vì vậy field NOT NULL (`title`, `status`, `priority`) phải chặn null (`not_nullable`).
    Field nullable thật sự cho phép xoá bằng null: `description`, `due_date`, và
    `assignee_id` (null = bỏ gán).
    """

    title: str | None = Field(
        default=None, min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH
    )
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    assignee_id: DbId | None = None

    _no_null = not_nullable("title", "status", "priority")

    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v: date | None) -> date | None:
        return _validate_due_date_not_in_past(v)


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)  # đọc thẳng từ ORM object

    id: int
    project_id: int
    assignee_id: int | None
    created_by: int
    status: TaskStatus
    created_at: datetime
    labels: list[LabelRead] = []
