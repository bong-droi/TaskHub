from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.endpoints import auth, health, tasks, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
# Toàn bộ /tasks yêu cầu đăng nhập (phân quyền chi tiết theo role: Ngày 4)
api_router.include_router(tasks.router, dependencies=[Depends(get_current_user)])
