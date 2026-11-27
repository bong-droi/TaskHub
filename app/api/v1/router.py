from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.endpoints import (
    auth,
    comments,
    health,
    labels,
    project_tasks,
    projects,
    tasks,
    users,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
# Mọi router dưới đây yêu cầu đăng nhập; phân quyền theo role nằm ở tầng service
protected = [Depends(get_current_user)]
api_router.include_router(workspaces.router, dependencies=protected)
api_router.include_router(projects.router, dependencies=protected)
api_router.include_router(project_tasks.router, dependencies=protected)
api_router.include_router(tasks.router, dependencies=protected)
api_router.include_router(labels.router, dependencies=protected)
api_router.include_router(comments.router, dependencies=protected)
