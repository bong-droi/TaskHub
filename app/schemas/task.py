from datetime import date, datetime
from enum import StrEnum

from pydantic import ConfigDict, Field, field_validator

from app.core.constants import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH, TITLE_MIN_LENGTH
from app.schemas.base import BaseSchema


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskBase(BaseSchema):
    title: str = Field(min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


class TaskCreate(TaskBase):
    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("due_date không được ở quá khứ")
        return v


class TaskUpdate(BaseSchema):
    """Dùng cho PATCH. Field vắng mặt = giữ nguyên.

    `exclude_unset=True` chỉ loại field client KHÔNG gửi, không loại `null` client gửi tường
    minh. Vì vậy field bắt buộc (NOT NULL) phải chặn null ở validator bên dưới; chỉ
    `description` và `due_date` (nullable thật sự) mới cho phép xoá bằng null.
    """

    title: str | None = Field(
        default=None, min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH
    )
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None

    @field_validator("title", "status", "priority")
    @classmethod
    def required_fields_cannot_be_null(cls, v):  # noqa: ANN001, ANN206
        if v is None:
            raise ValueError("Không được để null")
        return v


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)  # chuẩn bị cho ORM ở Ngày 2

    id: int
    status: TaskStatus
    created_at: datetime
