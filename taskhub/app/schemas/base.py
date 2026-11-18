from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Schema nền cho dữ liệu đầu vào: tự cắt khoảng trắng đầu/cuối của mọi chuỗi."""

    model_config = ConfigDict(str_strip_whitespace=True)
