"""Exception nghiệp vụ. Service chỉ raise các lớp này, không biết gì về HTTP."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code = 500
    headers: dict[str, str] | None = None

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BadRequestException(AppException):
    status_code = 400


class UnauthorizedException(AppException):
    status_code = 401
    headers = {"WWW-Authenticate": "Bearer"}  # chuẩn RFC 6750, Swagger cần header này


class ForbiddenException(AppException):
    status_code = 403


class NotFoundException(AppException):
    status_code = 404


class ConflictException(AppException):
    status_code = 409


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        # Giữ cùng format {"detail": ...} với HTTPException của FastAPI
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message}, headers=exc.headers
        )
