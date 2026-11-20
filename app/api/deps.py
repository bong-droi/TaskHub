"""Dependency Injection: get_db -> repositories -> service -> router; get_current_user."""

from typing import Annotated

import jwt
from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import API_PREFIX
from app.core.constants import DEFAULT_PAGE_LIMIT, INVALID_ACCESS_TOKEN, MAX_PAGE_LIMIT
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
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService

DbSession = Annotated[AsyncSession, Depends(get_db)]

# tokenUrl giúp Swagger hiện nút "Authorize" (Bearer auth scheme)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_PREFIX}/auth/login")


def get_access_control(db: DbSession) -> AccessControl:
    return AccessControl(WorkspaceMemberRepository(db))


def get_task_service(db: DbSession) -> TaskService:
    # Các repo dùng chung 1 session của request
    return TaskService(
        TaskRepository(db),
        ProjectRepository(db),
        UserRepository(db),
        get_access_control(db),
        LabelRepository(db),
    )


def get_label_service(db: DbSession) -> LabelService:
    return LabelService(LabelRepository(db), ProjectRepository(db), get_access_control(db))


def get_comment_service(db: DbSession) -> CommentService:
    return CommentService(
        CommentRepository(db), TaskRepository(db), ProjectRepository(db), get_access_control(db)
    )


def get_workspace_service(db: DbSession) -> WorkspaceService:
    return WorkspaceService(
        WorkspaceRepository(db),
        WorkspaceMemberRepository(db),
        UserRepository(db),
        get_access_control(db),
    )


def get_project_service(db: DbSession) -> ProjectService:
    return ProjectService(ProjectRepository(db), WorkspaceRepository(db), get_access_control(db))


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
    """Phân trang kiểu page + limit (theo đặc tả). page bắt đầu từ 1."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
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
