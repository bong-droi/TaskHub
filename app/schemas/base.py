from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.constants import FIELD_CANNOT_BE_NULL


class BaseSchema(BaseModel):
    """Schema nền cho dữ liệu đầu vào: tự cắt khoảng trắng đầu/cuối của mọi chuỗi."""

    model_config = ConfigDict(str_strip_whitespace=True)


def _reject_null(cls: Any, value: Any) -> Any:
    # Tham số đầu PHẢI tên đúng là `cls`: pydantic dựa vào tên này để coi đây là classmethod.
    if value is None:
        raise ValueError(FIELD_CANNOT_BE_NULL)
    return value


def not_nullable(*fields: str) -> Any:
    """Dùng trong schema PATCH cho các field NOT NULL trong DB.

    `exclude_unset=True` chỉ loại field client KHÔNG gửi, không loại `null` gửi tường minh, nên
    phải chặn null ở đây (nếu không sẽ ghi None vào cột NOT NULL và hỏng dữ liệu).

        class WorkspaceUpdate(BaseSchema):
            name: str | None = None
            _no_null = not_nullable("name")
    """
    return field_validator(*fields)(_reject_null)


reject_explicit_nulls = not_nullable
