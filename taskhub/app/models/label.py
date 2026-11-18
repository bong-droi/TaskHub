from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.task import task_labels


class Label(Base):
    __tablename__ = "labels"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50))
    color: Mapped[str] = mapped_column(String(7), default="#808080")

    project: Mapped["Project"] = relationship(back_populates="labels")  # noqa: F821
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        secondary=task_labels, back_populates="labels"
    )
