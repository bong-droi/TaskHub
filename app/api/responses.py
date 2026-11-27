"""Định nghĩa error responses dùng chung cho OpenAPI (Swagger UI / ReDoc)."""

from typing import Any

from app.schemas.error import ErrorResponse, InternalErrorResponse

_ERROR_SPECS: dict[int, tuple[type[ErrorResponse], str]] = {
    400: (ErrorResponse, "Dữ liệu hoặc nghiệp vụ không hợp lệ"),
    401: (ErrorResponse, "Chưa xác thực hoặc token không hợp lệ / hết hạn"),
    403: (ErrorResponse, "Không có quyền thực hiện thao tác hoặc tài khoản bị vô hiệu hoá"),
    404: (ErrorResponse, "Resource không tồn tại hoặc không có quyền truy cập"),
    409: (ErrorResponse, "Xung đột dữ liệu hoặc project đã được archive"),
    500: (InternalErrorResponse, "Lỗi hệ thống nội bộ"),
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Tạo mapping `responses=...` cho FastAPI router/endpoint từ danh sách mã lỗi HTTP."""
    return {
        code: {"model": _ERROR_SPECS[code][0], "description": _ERROR_SPECS[code][1]}
        for code in status_codes
    }
