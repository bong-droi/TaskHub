from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.responses import error_responses
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

api_router = APIRouter(responses=error_responses(500))
api_router.include_router(health.router)
api_router.include_router(auth.router)
# Mọi router dưới đây yêu cầu đăng nhập (có thể trả 401); phân quyền theo role nằm ở tầng service
auth_responses = error_responses(401)
api_router.include_router(users.router, responses=auth_responses)
protected = [Depends(get_current_user)]
api_router.include_router(workspaces.router, dependencies=protected, responses=auth_responses)
api_router.include_router(projects.router, dependencies=protected, responses=auth_responses)
api_router.include_router(project_tasks.router, dependencies=protected, responses=auth_responses)
api_router.include_router(tasks.router, dependencies=protected, responses=auth_responses)
api_router.include_router(labels.router, dependencies=protected, responses=auth_responses)
api_router.include_router(comments.router, dependencies=protected, responses=auth_responses)
