"""Exception nghiệp vụ + handler toàn cục. Service chỉ raise các lớp này, không biết gì về HTTP."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.constants import DATA_CONFLICT, INTERNAL_ERROR

logger = logging.getLogger("taskhub.errors")


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


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        # Giữ cùng format {"detail": ...} với HTTPException của FastAPI
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message}, headers=exc.headers
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        # Vi phạm ràng buộc DB lọt qua tầng service (vd 2 request cùng lúc): 409 thay vì 500
        logger.warning("IntegrityError rid=%s: %s", _request_id(request), exc.orig)
        return JSONResponse(status_code=409, content={"detail": DATA_CONFLICT})

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Không bao giờ trả stack trace/chi tiết nội bộ cho client; log đầy đủ kèm request id
        rid = _request_id(request)
        logger.error("Unhandled error rid=%s", rid, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": INTERNAL_ERROR, "request_id": rid},
            headers={"X-Request-ID": rid} if rid else None,
        )
