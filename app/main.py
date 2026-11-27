import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.cache import close_cache_backend
from app.core.config import API_PREFIX, APP_NAME, APP_VERSION, settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import RequestContextMiddleware
from app.db.session import engine

logger = logging.getLogger("taskhub")
logging.basicConfig(level=settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s đang khởi động (APP_ENV=%s)...", APP_NAME, settings.APP_ENV)
    yield
    await close_cache_backend()  # đóng kết nối Redis
    await engine.dispose()  # đóng connection pool khi tắt app
    logger.info("%s đã dừng.", APP_NAME)


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="TaskHub - Hệ thống quản lý công việc (Task Management API)",
    lifespan=lifespan,
    # Không lộ tài liệu/schema API khi chạy production
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)
register_exception_handlers(app)
app.add_middleware(RequestContextMiddleware)
app.include_router(api_router, prefix=API_PREFIX)
