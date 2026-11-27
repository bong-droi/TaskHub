from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, Enum, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TITLE_MAX_LENGTH
from app.db.base import Base, CreatedAtMixin
from app.models.enums import TaskPriority, TaskStatus

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.label import Label
    from app.models.project import Project

# Bảng liên kết N-N thuần (không có thuộc tính thêm) -> dùng Table + `secondary`
task_labels = Table(
    "task_labels",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
)


class Task(CreatedAtMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(TITLE_MAX_LENGTH))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=20), default=TaskStatus.TODO, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, native_enum=False, length=20), default=TaskPriority.MEDIUM
    )
    due_date: Mapped[date | None] = mapped_column(Date)

    project: Mapped["Project"] = relationship(back_populates="tasks")
    # Chỉ nạp labels cho TaskRead; các bảng khác không dùng lazy="selectin" tràn lan
    labels: Mapped[list["Label"]] = relationship(
        secondary=task_labels, back_populates="tasks", lazy="selectin", passive_deletes=True
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )
