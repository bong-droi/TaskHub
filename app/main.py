import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import API_PREFIX, APP_NAME, APP_VERSION

logger = logging.getLogger("taskhub")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s đang khởi động...", APP_NAME)
    yield
    logger.info("%s đã dừng.", APP_NAME)


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="TaskHub - Hệ thống quản lý công việc (Task Management API)",
    lifespan=lifespan,
)
app.include_router(api_router, prefix=API_PREFIX)
