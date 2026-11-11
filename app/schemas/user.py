from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import FULL_NAME_MAX_LENGTH
from app.models.enums import UserRole
from app.schemas.auth import Password
from app.schemas.base import BaseSchema


class UserRead(BaseModel):
    """Không có hashed_password: tuyệt đối không trả ra ngoài."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserUpdate(BaseSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=FULL_NAME_MAX_LENGTH)


class PasswordChange(BaseModel):
    """Không strip: cả mật khẩu cũ lẫn mới phải giữ nguyên từng ký tự."""

    current_password: str
    new_password: Password
