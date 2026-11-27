from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Định dạng phản hồi lỗi chuẩn cho 400 / 401 / 403 / 404 / 409."""

    detail: str = Field(examples=["Thông báo lỗi chi tiết"])


class InternalErrorResponse(ErrorResponse):
    """Định dạng phản hồi lỗi 500 kèm request_id để tra cứu log."""

    request_id: str | None = Field(default=None, examples=["9f8c7b6a5d4e3f2a1b0c9d8e7f6a5b4c"])
