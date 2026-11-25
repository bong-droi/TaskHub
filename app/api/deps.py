"""Dependency Injection: get_db -> repositories -> service -> router; get_current_user."""

from typing import Annotated

import jwt
from fastapi import BackgroundTasks, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import API_PREFIX, settings
from app.core.constants import (
    DEFAULT_PAGE_LIMIT,
    INVALID_ACCESS_TOKEN,
    MAX_PAGE_LIMIT,
    MAX_PAGE_NUMBER,
)
from app.core.email import EmailBackend, get_email_backend
from app.core.exceptions import UnauthorizedException
from app.core.security import ACCESS, decode_token
from app.db.session import get_db
from app.models import User
from app.repositories.comment_repository import CommentRepository
from app.repositories.label_repository import LabelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.repositories.workspace_repository import (
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from app.services.access import AccessControl
from app.services.auth_service import AuthService
from app.services.comment_service import CommentService
from app.services.label_service import LabelService
from app.services.notifier import Notifier
from app.services.project_service import ProjectService
from app.services.resource_access import ResourceAccess
from app.services.task_cache import TaskListCache
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService

DbSession = Annotated[AsyncSession, Depends(get_db)]

# tokenUrl giúp Swagger hiện nút "Authorize" (Bearer auth scheme)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_PREFIX}/auth/login")


def get_access_control(db: DbSession) -> AccessControl:
    return AccessControl(WorkspaceMemberRepository(db))


def get_task_list_cache(
    backend: Annotated[CacheBackend, Depends(get_cache_backend)],
) -> TaskListCache:
    return TaskListCache(backend, settings.CACHE_TTL_SECONDS)


def get_notifier(
    background: BackgroundTasks,  # cùng một đối tượng với BackgroundTasks của endpoint
    backend: Annotated[EmailBackend, Depends(get_email_backend)],
) -> Notifier:
    return Notifier(background, backend)


TaskListCacheDep = Annotated[TaskListCache, Depends(get_task_list_cache)]
NotifierDep = Annotated[Notifier, Depends(get_notifier)]


def get_resources(db: DbSession) -> ResourceAccess:
    """Một đối tượng dùng chung cho mọi service: lấy resource + kiểm quyền + kiểm archive."""
    return ResourceAccess(
        get_access_control(db),
        WorkspaceRepository(db),
        ProjectRepository(db),
        TaskRepository(db),
        LabelRepository(db),
        CommentRepository(db),
    )


ResourcesDep = Annotated[ResourceAccess, Depends(get_resources)]


def get_task_service(
    db: DbSession, resources: ResourcesDep, cache: TaskListCacheDep, notifier: NotifierDep
) -> TaskService:
    return TaskService(TaskRepository(db), UserRepository(db), resources, cache, notifier)


def get_label_service(
    db: DbSession, resources: ResourcesDep, cache: TaskListCacheDep
) -> LabelService:
    return LabelService(LabelRepository(db), resources, cache)


def get_comment_service(db: DbSession, resources: ResourcesDep) -> CommentService:
    return CommentService(CommentRepository(db), resources)


def get_workspace_service(db: DbSession, resources: ResourcesDep) -> WorkspaceService:
    return WorkspaceService(
        WorkspaceRepository(db), WorkspaceMemberRepository(db), UserRepository(db), resources
    )


def get_project_service(
    db: DbSession, resources: ResourcesDep, cache: TaskListCacheDep
) -> ProjectService:
    return ProjectService(ProjectRepository(db), resources, cache)


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(UserRepository(db), RefreshTokenRepository(db))


def get_user_service(db: DbSession) -> UserService:
    return UserService(UserRepository(db), RefreshTokenRepository(db))


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    try:
        payload = decode_token(token, ACCESS)  # refresh token KHÔNG dùng được ở đây
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise UnauthorizedException(INVALID_ACCESS_TOKEN) from None
    user = await UserRepository(db).get(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedException(INVALID_ACCESS_TOKEN)
    return user


class Pagination:
    """Phân trang kiểu page + limit (theo đặc tả). page bắt đầu từ 1, tối đa MAX_PAGE_NUMBER để
    offset không tràn số nguyên của DB."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, le=MAX_PAGE_NUMBER)] = 1,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    ) -> None:
        self.page = page
        self.limit = limit

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.limit


CurrentUser = Annotated[User, Depends(get_current_user)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
PaginationDep = Annotated[Pagination, Depends()]
