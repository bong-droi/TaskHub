from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

from app.core.constants import BCRYPT_MAX_BYTES, FULL_NAME_MAX_LENGTH, PASSWORD_MIN_LENGTH


def _bcrypt_limit(v: str) -> str:
    # Đếm theo byte, vì ký tự tiếng Việt chiếm nhiều hơn 1 byte
    if len(v.encode()) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Mật khẩu tối đa {BCRYPT_MAX_BYTES} byte")
    return v


Password = Annotated[str, Field(min_length=PASSWORD_MIN_LENGTH), AfterValidator(_bcrypt_limit)]


class RegisterRequest(BaseModel):
    """Cố ý KHÔNG kế thừa BaseSchema: mật khẩu tuyệt đối không được tự cắt khoảng trắng
    (người dùng có thể cố ý đặt mật khẩu có dấu cách). Chỉ `full_name` được strip."""

    email: EmailStr
    password: Password
    full_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=FULL_NAME_MAX_LENGTH),
    ]
    # Không có field `role`: client không được tự chọn quyền (mass assignment)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
