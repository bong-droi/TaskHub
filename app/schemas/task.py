from datetime import date, datetime

from pydantic import ConfigDict, Field, field_validator

from app.core.constants import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH, TITLE_MIN_LENGTH
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.base import BaseSchema
from app.schemas.label import LabelRead

__all__ = [
    "TaskCreate",
    "TaskCreateInProject",
    "TaskPriority",
    "TaskRead",
    "TaskStatus",
    "TaskUpdate",
]


class TaskBase(BaseSchema):
    title: str = Field(
        min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH, examples=["Viết tài liệu API"]
    )
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


class _TaskCreateBase(TaskBase):
    """Phần chung của mọi schema TẠO task (không đặt vào TaskBase vì TaskRead cũng kế thừa:
    task cũ có due_date đã qua vẫn phải đọc được)."""

    assignee_id: int | None = Field(default=None, gt=0)

    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("due_date không được ở quá khứ")
        return v


class TaskCreate(_TaskCreateBase):
    project_id: int = Field(gt=0)


class TaskCreateInProject(_TaskCreateBase):
    """Body của POST /projects/{id}/tasks: project_id lấy từ URL, không nhận từ body."""


class TaskUpdate(BaseSchema):
    """Dùng cho PATCH. Field vắng mặt = giữ nguyên.

    `exclude_unset=True` chỉ loại field client KHÔNG gửi, không loại `null` client gửi tường
    minh. Vì vậy field NOT NULL (`title`, `status`, `priority`) phải chặn null ở validator.
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
    assignee_id: int | None = Field(default=None, gt=0)

    @field_validator("title", "status", "priority")
    @classmethod
    def required_fields_cannot_be_null(cls, v):  # noqa: ANN001, ANN206
        if v is None:
            raise ValueError("Không được để null")
        return v


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)  # đọc thẳng từ ORM object

    id: int
    project_id: int
    assignee_id: int | None
    created_by: int | None
    status: TaskStatus
    created_at: datetime
    labels: list[LabelRead] = []
