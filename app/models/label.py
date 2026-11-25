from sqlalchemy import ForeignKey, Index, String, func
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


# Tên label duy nhất trong project, KHÔNG phân biệt hoa thường: "Bug" và "bug" là một.
# Phải là unique index trên lower(name): ràng buộc (project_id, name) thường phân biệt hoa thường
# nên hai request "Bug"/"bug" đồng thời vẫn lọt cả hai. Service (LabelRepository.get_by_name) dùng
# cùng biểu thức lower() để kiểm tra trước và báo lỗi thân thiện; index này là chốt chặn cuối.
# Lưu ý: lower() của SQLite chỉ xử lý ASCII ("Đỏ" khác "đỏ"); PostgreSQL xử lý đủ Unicode.
Index("uq_labels_project_id_lower_name", Label.project_id, func.lower(Label.name), unique=True)
