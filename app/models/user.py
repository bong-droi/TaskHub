from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.workspace import Workspace, WorkspaceMember


class User(CreatedAtMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20), default=UserRole.MEMBER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owned_workspaces: Mapped[list["Workspace"]] = relationship(back_populates="owner")
    memberships: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
